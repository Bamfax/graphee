#!/usr/bin/env python
# coding=utf-8

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "../lib"))
import re, json
from neo4j import GraphDatabase 
from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option, validators
from helperfuncs import string_hascontent, string_preformat

@Configuration( requires_preop = True, run_in_preview = False )
class creategraphjson(ReportingCommand):
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

    inputfield = Option(
        doc='''
        **Syntax:** **inputfield=***<inputfield>*
        **Description:** Name of the field which is taken as inputfield. Default is \"json_obj\". ''',
        require=False, validate=validators.Fieldname(), default='json_obj' )

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
        self.input_field = self.inputfield
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
    def create_node( self, tx, id: str, labels: list, props :dict ):
        labelsstr = ':'.join([labels])
        propsstr = self.build_paramsstr(props)
        query = "{0} ({1}:{2} {3}) RETURN ID({1})".format( self.create_mode, id, labelsstr, propsstr )
        result = tx.run( query )

        nodes_id = []
        for record in result:
            nodes_id.append( record['ID({0})'.format(id)] )
        if not len( nodes_id ) > 1:
            return nodes_id[0]
        else:
            errormsg = ( 'ERROR: In create_node(): Created one node, but more than one node was returned.' )
            self.error_exit( sys.exc_info(), errormsg )
    #------------------   def create_node(): end           -----------------#

    #------------------   def create_rel(): start          -----------------#
    def create_rel( self, tx, src_node_id: str, dst_node_id: str, reltype: str, props: dict ):
        try:
            src_node_id = self.nodesToRef[src_node_id]
            dst_node_id = self.nodesToRef[dst_node_id]
        except:
            errormsg =  'ERROR: In create_rel(): Seems like the source and/or dest node of the rel to be created are null. Are you sure you created them already?'
            self.error_exit( sys.exc_info(), str(errormsg) )


        propsstr = self.build_paramsstr(props)
        query = ( 'MATCH (src) WHERE id(src) = $src_node_id ' +
                  'MATCH (dst) WHERE id(dst) = $dst_node_id ' +
                  '{0} (src)-[rel:{1} {2}]->(dst) RETURN ID(rel)' ).format( self.create_mode, reltype, propsstr )
        result = tx.run( query, src_node_id=src_node_id, dst_node_id=dst_node_id )

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
    def graphcreator( self, nodesAndRels: list ):
        objsToCreate = [record[self.input_field] for record in nodesAndRels if record[self.input_field]]
        self.nodesToRef = {}

        driver = GraphDatabase.driver( self.neo4j_uri['uri'], auth = ( self.neo4j_accoount['username'], self.neo4j_accoount['password' ]) )
        with driver.session() as session:
            if  len(objsToCreate) >= 1:
                for json_str in objsToCreate:
                    pyobj = json.loads( json_str )
                    obj_type = pyobj.get( 'obj_type' )
                    if obj_type == 'node':
                        node_ref = pyobj.get( 'node_ref' )
                        node_label = pyobj.get( 'node_label' )
                        node_props = {  key[self.prop_prefix_len:]: val for key, val in pyobj.items()
                                        if key.startswith(self.prop_prefix) }
                        node_identity = session.execute_write( self.create_node, node_ref, node_label, node_props )
                        self.nodesToRef[ node_ref ] = node_identity
                    elif obj_type == 'rel':
                        rel_type = pyobj.get('rel_type')
                        rel_src_node = pyobj.get('rel_src_node')
                        rel_dst_node = pyobj.get('rel_dst_node')
                        rel_props = {  key[self.prop_prefix_len:]: val for key, val in pyobj.items()
                                        if key.startswith(self.prop_prefix) }
                        rel_identity = session.execute_write( self.create_rel, rel_src_node, rel_dst_node, rel_type, rel_props )
                        
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
                if record[self.input_field]:
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

dispatch( creategraphjson, sys.argv, sys.stdin, sys.stdout, __name__ )
