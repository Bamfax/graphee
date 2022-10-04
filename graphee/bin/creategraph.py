#!/usr/bin/env python
# coding=utf-8

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "../lib"))
import re, json
from neo4j import GraphDatabase 
from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option, validators
from helperfuncs import string_hascontent, string_preformat

@Configuration( requires_preop = True, run_in_preview = False )
class creategraph(ReportingCommand):
    from classsharedfuncs import sharedprepare

    uri = Option(
        doc='''
        **Syntax:** **uri=***<URI_ID>*
        **Description:** URI_ID: ID of the Neo4j URI entry as specified in configuration page under "Neo4j URI" ''',
        require=True )

    account = Option(
        doc='''
        **Syntax:** **account=***<Account_ID>*
        **Description:** Account_ID: ID of the Neo4j Account entry as specified in configuration page under "Neo4j Accounts" ''',
        require=True )

    noact = Option(
        doc='''
        **Syntax:** **noact=***<"true"|"false">*
        **Description:** No action. Default is \"false\" ''',
        require=False, validate=validators.Boolean(), default='false' )

    mode = Option(
        doc='''
        **Syntax:** **mode=***<"MERGE"|"CREATE">*
        **Description:** Cypher command with which the nodes and/or relationsships are being created. Choose between \"merge\" and \"create\". Default is \"merge\" ''',
        require=False, validate=validators.Set('merge', 'create'), default='merge' )

    propsprefix = Option(
        doc='''
        **Syntax:** **propsprefix=***<properties_prefix>*
        **Description:** Selector for the properties fields. Choose which fields are taken/read from the inputfield by prepending their names with this prefix. This prefix is then removed from the fieldname in the graph. Default is \"p_\". ''',
        require=False, default='p_' )

    #------------------   def prepare(): start             -----------------#
    def prepare(self):
        """
        Prepare, customcommand specific. 
        :return: None
        """
        self.logger.info('prepare start: %s', self)
 
        self.app_id, self.conf_uris_page, self.conf_accounts_page, self.neo4j_uri, self.neo4j_accoount, self.noact = self.sharedprepare()

        self.create_mode = str(self.mode).upper()
        self.prop_prefix = self.propsprefix
        self.prop_prefix_len = len(self.propsprefix)
        
        self.logger.debug( 'prepare() done.' )
    #------------------   def prepare(): end               -----------------#

    #------------------   def build_paramsstr(): start     -----------------#
    def build_paramsstr( self, props: dict ):
        if props == None:
            return '' 

        propslist = []
        for pkey, pval in props.items():
            val_escaped = str(pval).replace('\\', '\\\\').replace(r'"', r'\"').replace(r"'", r'\'')
            propstr = '{0}: \'{1}\''.format( str(pkey), val_escaped )
            propslist.append(propstr)
        unwrapped_propsstr = ', '.join(propslist)
        outstring = '{{ {0} }}'.format( unwrapped_propsstr )
        return outstring
    #------------------   def build_paramsstr(): end       -----------------#

    #------------------   def create_node(): start         -----------------#
    def create_node( self, tx, ref: str, labels: list, props :dict ):
        #labelsstr = ':'.join([labels])
        #wrapped_props = { 'wrapped_props': props }
        #query = "CREATE ({0}:{1} $wrapped_props) RETURN ID({0})".format(id, labelsstr)
        #result = tx.run( query, wrapped_props)

        labelsstr = ':'.join([labels])
        propsstr = self.build_paramsstr(props)
        query = "{0} ({1}:{2} {3}) RETURN ID({1})".format( self.create_mode, ref, labelsstr, propsstr )
        result = tx.run( query )

        nodeIds = []
        for record in result:
            nodeIds.append( record['ID({0})'.format(ref)] )
        if not len( nodeIds ) > 1:
            return nodeIds[0]
        else:
            errormsg = ( 'ERROR: In create_node(): Created one node, but more than one node was returned.' )
            self.error_exit( sys.exc_info(), errormsg )
    #------------------   def create_node(): end           -----------------#

    #------------------   def create_rel(): start          -----------------#
    def create_rel( self, tx, src_node_ref: str, dst_node_ref: str, reltype: str, props: dict ):
        try:
            src_node_id = self.nodeRefToId[src_node_ref]
            dst_node_id = self.nodeRefToId[dst_node_ref]
        except:
            errormsg =  'ERROR: In create_rel(): Seems like the source and/or dest node of the rel to be created are null. Are you sure you created them already?'
            self.error_exit( sys.exc_info(), str(errormsg) )


        propsstr = self.build_paramsstr(props)
        query = ( 'MATCH (src) WHERE id(src) = $cypher_src_node_id ' +
                  'MATCH (dst) WHERE id(dst) = $cypher_dst_node_id ' +
                  '{0} (src)-[rel:{1} {2}]->(dst) RETURN ID(rel)' ).format( self.create_mode, reltype, propsstr )
        result = tx.run( query, cypher_src_node_id=src_node_id, cypher_dst_node_id=dst_node_id )

        rels_id = []
        for record in result:
            rels_id.append( record['ID(rel)'] )
        if not len( rels_id ) > 1:
            return rels_id[0]
        else:
            errormsg = ( 'ERROR: In |cypher create_rel(): Created one relationship, but more than one relationship was returned.' )
            self.error_exit( sys.exc_info(), errormsg )
    #------------------   def create_rel(): end            -----------------#

    #------------------   def graphcreator(): start       -----------------#
    def graphcreator( self, nodesAndRelEvents: list ):
        nodesToCreate = [event for event in nodesAndRelEvents if event['obj_type'] == 'node']
        relsToCreate  = [event for event in nodesAndRelEvents if event['obj_type'] == 'rel' ]
        self.nodeRefToId = {}

        driver = GraphDatabase.driver( self.neo4j_uri['uri'], auth = ( self.neo4j_accoount['username'], self.neo4j_accoount['password' ]) )

        with driver.session() as session:
            if  len(nodesToCreate) >= 1:
                for nodeToCreate in nodesToCreate:
                    # collect properties in fields
                    nodeprops = {}
                    prefixrex = '^{0}(.+)$'.format(self.prop_prefix)
                    for key, value in nodeToCreate.items():
                        node_propkey_capture = re.search(prefixrex, key)
                        if not node_propkey_capture == None and string_hascontent(value):
                            newkey = node_propkey_capture.group(1)
                            nodeprops[ newkey ] = value

                    node_id = session.execute_write( self.create_node, nodeToCreate['node_ref'], nodeToCreate['node_label'], nodeprops )
                    self.nodeRefToId[ nodeToCreate['node_ref'] ] = node_id

            if  len(relsToCreate) >= 1:
                for relToCreate in relsToCreate:
                    # collect properties in fields
                    relprops = {}
                    prefixrex = '^{0}(.+)$'.format(self.prop_prefix)
                    for key, value in relToCreate.items():
                        rel_propkey_capture = re.search(prefixrex, key)
                        if not rel_propkey_capture == None and string_hascontent(value):
                            relprops[ rel_propkey_capture.group(1) ] = value

                    rel_id = session.execute_write( self.create_rel, relToCreate['rel_src_node'], relToCreate['rel_dst_node'], relToCreate['rel_type'], relprops )

        self.logger.info( 'graphcreator: done.' )
    #------------------   def graphcreator(): end         -----------------#

    #------------------   def map(): start                -----------------#
    @Configuration( local = True, distributed = False )
    def map(self, records):
        """ 
        map() is not being executed when self.prepare is being used. self.phase is then always 'reduce' and never 'map'.
        using a decorater @Configuration(requires_preop = True) or "requires_preop = true" in commands.conf does not change this.
        """

        try:
            for record in records:
                yield record
            
        except Exception as ex:
            exceptiondesc = str(type(ex).__name__)
            errormsg = ( 'ERROR: Error executing |creategraph in map(). Exception: %s' % ( exceptiondesc ) )
            self.error_exit( sys.exc_info(), errormsg )
    #------------------   def map(): end                  -----------------#

    #------------------   def reduce(): start             -----------------#
    def reduce(self, records):
        try:
            nodesAndRelsFromSplunk = []

            for record in records:
                if record['obj_type']:
                    nodesAndRelsFromSplunk.append(record)

            if self.noact == False and len(nodesAndRelsFromSplunk) >= 1:
                self.graphcreator(nodesAndRelsFromSplunk)
                
            for nodeOrRelFromSplunk in nodesAndRelsFromSplunk:
                yield nodeOrRelFromSplunk
            
        except Exception as ex:
            exdesc_orig = '{0}: {1}: {2}'.format(str(type(ex).__name__), str(ex.args), str(ex.__doc__))
            exdesc_sani = string_preformat(exdesc_orig)
            errormsg =  'ERROR: In reduce(): {0}'.format( exdesc_sani )
            self.error_exit( sys.exc_info(), str(errormsg) )
    #------------------   def reduce(): end               -----------------#

dispatch( creategraph, sys.argv, sys.stdin, sys.stdout, __name__ )
