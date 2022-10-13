#!/usr/bin/env python
# coding=utf-8

from operator import le
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "../lib"))
import re, json
from neo4j import GraphDatabase 
from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option, validators
from helperfuncs import string_hascontent, string_preformat
import debugpy

@Configuration( requires_preop = True, run_in_preview = False )
class creategraphbatchedjson(ReportingCommand):
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
        self.input_field = self.inputfield
        self.prop_prefix = self.propsprefix
        self.prop_prefix_len = len(self.propsprefix)

        self.batchsize = 500
        self.driver = GraphDatabase.driver( self.neo4j_uri['uri'], auth = ( self.neo4j_accoount['username'], self.neo4j_accoount['password' ]) )

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
            errormsg = ( 'ERROR: In create_rel(): Created one relationship, but more than one relationship was returned.' )
            self.error_exit( sys.exc_info(), errormsg )
    #------------------   def create_rel(): end            -----------------#

    #------------------   def batchcreate_node(): start    -----------------#
    def batchcreate_node( self, tx, labelset: str, nodes: list ):
        nodesCreatedRefToId = {}

        query =  """UNWIND $nodes as node \n""" \
                f"""CREATE (n:{labelset}) \n""" \
                 """SET n += node.properties \n""" \
                 """RETURN COLLECT(ID(n))"""

        result = tx.run( query, nodes=nodes )

        for record in result:
            nodeIDs = record[0]

            countNodes = len( nodes )
            countNodesCreated = len( nodeIDs )

            if countNodesCreated == countNodes:
                for i in range(len(nodes)):
                    nodesCreatedRefToId[nodes[i]['node_ref']] = nodeIDs[i]

                return nodesCreatedRefToId
            else:
                errormsg = ( f'ERROR: In create_node(): {countNodes} nodes to be created, but only {countNodesCreated} nodes confirmed' )
                self.error_exit( sys.exc_info(), errormsg )

    #------------------   def batchcreate_node(): end       -----------------#

    #------------------   def nodebatcher(): start    -----------------#
    def nodebatcher( self, labelstr: str, nodes: list ):
        nodesCreated = {}

        with self.driver.session() as session:
            for i in range(0, len(nodes), self.batchsize):
                fromIdx = i
                toIdx = i+self.batchsize
                nodeBatchCreated = session.execute_write(self.batchcreate_node, labelstr, nodes[fromIdx:toIdx])
                nodesCreated = { **nodesCreated, **nodeBatchCreated }
        
        return nodesCreated
    #------------------   def nodebatcher(): end       -----------------#

    #------------------   def create_nodes(): start         -----------------#
    def create_nodes( self, nodes: list ):
        nodeRefToId = {}
        nodesByLabel = {}

        for node in nodes:
            newNode = {}

            labelset = node.get('node_label')
            if isinstance(labelset, list):
                labelstr = ':'.join(labelset)
            else:
                labelstr = labelset
            properties = { key[self.prop_prefix_len:]: val for key, val in node.items() if key.startswith(self.prop_prefix) }
            node_ref = node.get('node_ref')
            if not nodeRefToId.get(node_ref):
                nodeRefToId[node_ref] = 'na'
            else:
                errormsg = ( f'ERROR: In create_nodes(): Duplicate node_ref found in inputstream: {node_ref}. |creategraphbatchedjson cannot work with dups. Please dedup beforehand. Aborting.' )
                self.error_exit( sys.exc_info(), errormsg )

            newNode['node_ref']   = node_ref
            newNode['node_label'] = labelstr
            newNode['properties'] = properties

            if not nodesByLabel.get(labelstr):
                nodesByLabel[labelstr] = []
            
            nodesByLabel[labelstr].append(newNode)

        for labelstr, nodes in nodesByLabel.items():
            nodesCreated = self.nodebatcher( labelstr, nodes )
            for key, val in nodesCreated.items():
                nodeRefToId[key] = val

        for key, val in nodeRefToId.items():
            if val == 'na':
                errormsg = ( f'ERROR: In create_nodes(): The node {key} which should have been created was not. Aborting.' )
                self.error_exit( sys.exc_info(), errormsg )

        return nodeRefToId
    #------------------   def create_nodes(): end           -----------------#

    #------------------   def graphcreator(): start       -----------------#
    def graphcreator( self, nodesAndRels: list ):
        if len(nodesAndRels) >= 1:
            nodesToCreate = []
            relsToCreate = []

            for rec in nodesAndRels:
                if rec.get('obj_type') == 'node':
                    nodesToCreate.append(rec)
                elif rec.get('obj_type') == 'rel':
                    relsToCreate.append(rec)

        if len(nodesToCreate) >= 1:
            nodesCreated = self.create_nodes(nodesToCreate)
                       
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
        #debugpy.listen(("0.0.0.0", 5678))
        #debugpy.wait_for_client()

        try:
            splunkSetFull = []
            objsToProcess = []

            for record in records:
                splunkSetFull.append(record)
                inputfld = record.get(self.input_field)
                if string_hascontent(inputfld) :
                    obj = json.loads(inputfld)
                    objsToProcess.append(obj)

            if self.noact == False and len(objsToProcess) >= 1:
                self.graphcreator(objsToProcess)
                
            for splunkOrigRecord in splunkSetFull:
                yield splunkOrigRecord
            
        except Exception as ex:
            exdesc_orig = '{0}: {1}: {2}'.format(str(type(ex).__name__), str(ex.args), str(ex.__doc__))
            exdesc_sani = string_preformat(exdesc_orig)
            errormsg =  'ERROR: In reduce(): {0}'.format( exdesc_sani )
            self.error_exit( sys.exc_info(), str(errormsg) )
    #------------------   def reduce(): end               -----------------#

dispatch( creategraphbatchedjson, sys.argv, sys.stdin, sys.stdout, __name__ )
