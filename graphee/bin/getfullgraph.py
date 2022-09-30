#!/usr/bin/env python
# coding=utf-8

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib", "../lib"))
import re, json, time
import neo4j
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from helperfuncs import string_hascontent, string_preformat

@Configuration( local = True,  streaming = False )
class getgraphall(GeneratingCommand):
    from classsharedfuncs import sharedprepare

    uri = Option(
        doc='''
        **Syntax:** **uri=***<URI_ID>*
        **Description:** URI_ID: ID of the Neo4j URI entry as specified in configuration page under "Neo4j URI" ''',
        require=True, validate=validators.Fieldname() )
 
    account = Option(
        doc='''
        **Syntax:** **account=***<Account_ID>*
        **Description:** Account_ID: ID of the Neo4j Account entry as specified in configuration page under "Neo4j Accounts" ''',
        require=True, validate=validators.Fieldname() )

    noact = Option(
        doc='''
        **Syntax:** **noact=***<"true"|"false">*
        **Description:** No action. Default is \"false\" ''',
        require=False, validate=validators.Boolean(), default='false' )

    #------------------   def prepare(): start             -----------------#
    def prepare(self):
        """
        Prepare, customcommand specific. 
        :return: None
        """
        self.logger.info('prepare start: %s', self)
 
        self.app_id, self.conf_uris_page, self.conf_accounts_page, self.neo4j_uri, self.neo4j_accoount, self.noact = self.sharedprepare()

        self.logger.debug( 'prepare() done.' )
    #------------------   def prepare(): end               -----------------#

    #------------------   def querynodes(): start          -----------------#
    def querynodes( self, tx ):
        query = "MATCH (n) return n"
        results = tx.run( query ) 

        out = list()
        for record in results:
            outevent = { '_time': time.time(), 'obj_type': 'node', 'node_id': record['n'].id, 'node_labels': list(record['n'].labels) }
            
            nodeprops = dict()
            for key, val in record['n'].items():
                newkey = 'prop:{0}'.format( str( key ) )
                nodeprops[newkey] = val
            
            outevent.update( nodeprops )
            out.append(outevent)

        self.logger.debug( 'querynodes() done. ' )
        return out
    #------------------   def querynodes(): end            -----------------#

    #------------------   def queryrels(): start           -----------------#
    def queryrels( self, tx ):
        query = "MATCH ()-[r]->() return r"
        results = tx.run( query ) 

        out = list()
        for record in results:
            outevent = { '_time': time.time(), 'obj_type': 'rel', 'rel_id': record['r'].id, 'rel_type': record['r'].type }
            
            relprops = dict()
            for key, val in record['r'].items():
                newkey = 'prop:{0}'.format( str( key ) )
                relprops[newkey] = val
            
            outevent.update( relprops )
            out.append(outevent)

        self.logger.debug( 'queryrels() done. ' )
        return out
    #------------------   def queryrels(): end             -----------------#

    #------------------   def querygraph(): start          -----------------#
    def getfullgraph( self ):
        driver = neo4j.GraphDatabase.driver( self.neo4j_uri['uri'], auth = ( self.neo4j_accoount['username'], self.neo4j_accoount['password' ]) )

        results = list()
        with driver.session() as session:
            results = session.execute_read( self.querynodes )
            results.extend( session.execute_read( self.queryrels ) )

        return results

    #------------------   def querygraph(): end            -----------------#

    #------------------   def generate(): start            -----------------#
    def generate( self ):

        #try:
        #    text = f'Test Event {1}'
        #    yield {'_time': time.time(), 'event_no': 1, '_raw': text}
        
        if self.noact == True:
            text = 'NOACT was true, no action.'
            yield {'_time': time.time(), '_raw': text}
            return

        finalresults = list()
        try:
            finalresults = self.getfullgraph()
            emptydict_allkeys = dict.fromkeys( set().union(*finalresults), None )
            finalresults_normalized = [dict(emptydict_allkeys, **entry) for entry in finalresults]

            for event in finalresults_normalized:
                yield { **event, '_raw': str(event) }
                #yield { **event, '_raw': json.dumps(event) }

        except Exception as ex:
            exdesc_orig = '{0}: {1}: {2}'.format(str(type(ex).__name__), str(ex.args), str(ex.__doc__))
            exdesc_sani = string_preformat(exdesc_orig)
            errormsg =  'ERROR: In generate(): {0}'.format( exdesc_sani )
            self.error_exit( sys.exc_info(), str(errormsg) )
    #------------------   def generate(): end              -----------------#


dispatch( getgraphall, sys.argv, sys.stdin, sys.stdout, __name__ )
