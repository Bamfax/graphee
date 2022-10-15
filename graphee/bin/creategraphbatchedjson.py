#!/usr/bin/env python
# coding=utf-8

from operator import le
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "../lib"))
import re, json
from neo4j import GraphDatabase 
from splunklib.searchcommands import dispatch, ReportingCommand, Configuration, Option, validators
from helperfuncs import string_hascontent, string_preformat
from collections import namedtuple
#import debugpy

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

    #------------------   def batchcreate_rel(): start     -----------------#
    def batchcreate_rel( self, tx, reltype: str, rels: list ):
        relsCreatedSrcDstToId = {}
        SrcDst = namedtuple( 'SrcDst', ['rel_type', 'src', 'dst'] )

        query =  """UNWIND $rels as rel \n""" \
                 """MATCH (src) WHERE ID(src) = rel.src_node_id \n""" \
                 """MATCH (dst) WHERE ID(dst) = rel.dst_node_id \n""" \
                f"""CREATE (src)-[r:{reltype}]->(dst) \n""" \
                 """SET r += rel.properties \n""" \
                 """RETURN COLLECT(ID(r))"""

        result = tx.run( query, rels=rels )

        for record in result:
            relIDs = record[0]

            countRels = len( rels )
            countRelsCreated = len( relIDs )

            if countRelsCreated == countRels:
                for i in range( countRels ):
                    src_node_id = rels[i]['src_node_id']
                    dst_node_id = rels[i]['dst_node_id']
                    srcDstRef = SrcDst( rel_type=reltype, src=src_node_id, dst=dst_node_id )
                    relsCreatedSrcDstToId[srcDstRef] = relIDs[i]

                return relsCreatedSrcDstToId
            else:
                errormsg = ( f'ERROR: In create_node(): {countRels} nodes to be created, but only {countRelsCreated} nodes confirmed' )
                self.error_exit( sys.exc_info(), errormsg )
    #------------------   def batchcreate_rel(): end       -----------------#

    #------------------   def relbatcher(): start          -----------------#
    def relbatcher( self, reltype: str, rels: list ):
        relsCreated = {}

        with self.driver.session() as session:
            for i in range(0, len(rels), self.batchsize):
                fromIdx = i
                toIdx = i+self.batchsize
                relBatchCreated = session.execute_write(self.batchcreate_rel, reltype, rels[fromIdx:toIdx])
                relsCreated = { **relsCreated, **relBatchCreated }
       
        return relsCreated
    #------------------   def relbatcher(): end             -----------------#

    #------------------   def create_rels(): start          -----------------#
    def create_rels( self, rels: list, nodeRefToId: dict ):
        relSrcDstToId = {}
        relsByLabel = {}
        SrcDst = namedtuple( 'SrcDst', ['rel_type', 'src', 'dst'] )

        for rel in rels:
            newRel = {}

            rel_type = rel.get('rel_type')
            src_node_ref = rel['rel_src_node']
            dst_node_ref = rel['rel_dst_node']
            src_node_id = nodeRefToId.get( src_node_ref )
            dst_node_id = nodeRefToId.get( dst_node_ref )
            if src_node_id is None:
                errormsg =  f'ERROR: In create_rels(): The src node {src_node_ref} of the rel to be created was not found. Are you sure you created them already?'
                self.error_exit( sys.exc_info(), str(errormsg) )
            if dst_node_id is None:
                errormsg =  f'ERROR: In create_rels(): The dest node {dst_node_ref} of the rel to be created was not found. Are you sure you created them already?'
                self.error_exit( sys.exc_info(), str(errormsg) )
            srcDstRef = SrcDst( rel_type=rel_type, src=src_node_id, dst=dst_node_id )

            properties = { key[self.prop_prefix_len:]: val for key, val in rel.items() if key.startswith(self.prop_prefix) }

            if relSrcDstToId.get( srcDstRef ) is None:
                relSrcDstToId[srcDstRef] = 'na'
            else:
                errormsg = ( f'ERROR: In create_rels(): Duplicate rel found in inputstream: {srcDstRef} rel_type: {rel_type} rel_src_node: {src_node_ref} rel_dst_node: {dst_node_ref}. |creategraphbatchedjson cannot work with dups. Please dedup beforehand. Aborting.' )
                self.error_exit( sys.exc_info(), errormsg )

            newRel['src_node_id'] = src_node_id
            newRel['dst_node_id'] = dst_node_id
            newRel['properties']   = properties

            if relsByLabel.get(rel_type) is None:
                relsByLabel[rel_type] = []
            
            relsByLabel[rel_type].append(newRel)

        for reltypeToBatch, relsToBatch in relsByLabel.items():
            relsCreated = self.relbatcher( reltypeToBatch, relsToBatch )
            for key, val in relsCreated.items():
                relSrcDstToId[key] = val

        for key, val in relSrcDstToId.items():
            if val == 'na':
                errormsg = ( f'ERROR: In create_nodes(): The rel {key} which should have been created was not. Aborting.' )
                self.error_exit( sys.exc_info(), errormsg )

        return relSrcDstToId
    #------------------   def create_rels(): end            -----------------#

    #------------------   def batchcreate_node(): start     -----------------#
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
                for i in range( countNodes ):
                    nodesCreatedRefToId[nodes[i]['node_ref']] = nodeIDs[i]

                return nodesCreatedRefToId
            else:
                errormsg = ( f'ERROR: In create_node(): {countNodes} nodes to be created, but only {countNodesCreated} nodes confirmed' )
                self.error_exit( sys.exc_info(), errormsg )
    #------------------   def batchcreate_node(): end        -----------------#

    #------------------   def nodebatcher(): start           -----------------#
    def nodebatcher( self, labelstr: str, nodes: list ):
        nodesCreated = {}

        with self.driver.session() as session:
            for i in range(0, len(nodes), self.batchsize):
                fromIdx = i
                toIdx = i+self.batchsize
                nodeBatchCreated = session.execute_write(self.batchcreate_node, labelstr, nodes[fromIdx:toIdx])
                nodesCreated = { **nodesCreated, **nodeBatchCreated }
        
        return nodesCreated
    #------------------   def nodebatcher(): end             -----------------#

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
            if nodeRefToId.get(node_ref) is None:
                nodeRefToId[node_ref] = 'na'
            else:
                errormsg = ( f'ERROR: In create_nodes(): Duplicate node_ref found in inputstream: {node_ref}. |creategraphbatchedjson cannot work with dups. Please dedup beforehand. Aborting.' )
                self.error_exit( sys.exc_info(), errormsg )

            newNode['node_ref']   = node_ref
            newNode['node_label'] = labelstr
            newNode['properties'] = properties

            if nodesByLabel.get(labelstr) is None:
                nodesByLabel[labelstr] = []
            
            nodesByLabel[labelstr].append(newNode)

        for labelstrToBatch, nodesToBatch in nodesByLabel.items():
            nodesCreated = self.nodebatcher( labelstrToBatch, nodesToBatch )
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
            self.nodeRefToId   = self.create_nodes( nodesToCreate )
            self.relSrcDstToId = self.create_rels( relsToCreate, self.nodeRefToId )
                       
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
