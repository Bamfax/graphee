require([
    "jquery",
    "splunkjs/mvc",
    "splunkjs/mvc/searchmanager",
    "splunkjs/mvc/searchbarview",
    "splunkjs/mvc/searchcontrolsview",
    "splunkjs/mvc/simplexml/ready!"
], function(
    $,
    mvc,
    SearchManager,
    SearchbarView,
    SearchControlsView
) {

    var tokens = mvc.Components.get("default");

    // Create the search manager
    var mysearch = new SearchManager({
        id: "base",
        autostart: "false",
        app: "search",
        preview: true,
        cache: true,
        status_buckets: 300,
        required_field_list: "*",
        search: ""
    });

    // Create the views
    var mysearchbar = new SearchbarView ({
        id: "searchbar1",
        managerid: "base",
        el: $("#mysearchbar1")
    }).render();

    var mysearchcontrols = new SearchControlsView ({
        id: "searchcontrols1",
        managerid: "base",
        el: $("#mysearchcontrols1")
    }).render();

    // When the query in the searchbar changes, update the search manager
    mysearchbar.on("change", function() {
        mysearch.settings.unset("search");
        mysearch.settings.set("search", mysearchbar.val());

        // set token value with search string
        var searchString = mysearchbar.val();

        //Collect tokens from the dashboard
        function setToken(name, value) {
          defaultTokenModelun.set(name, value);
          submittedTokenModelun.set(name, value);
        }
        function unsetToken(name) {
          defaultTokenModelun.unset(name);
          submittedTokenModelun.unset(name);
        }
        var defaultTokenModelun = mvc.Components.getInstance('default', { create: true });
        var submittedTokenModelun = mvc.Components.getInstance('submitted', { create: true });

        //Show the edit panel
        setToken("searchString",searchString);

        setToken("earliest",mysearch.settings.attributes.earliest_time);
        setToken("latest",mysearch.settings.attributes.latest_time);

        console.log("Eariest time: " + defaultTokenModelun.get("earliest"));
        console.log("Latest time: " + defaultTokenModelun.get("latest"));
        //unsetToken("beforeSearch");
    });

    // When the timerange in the searchbar changes, update the search manager
    mysearchbar.timerange.on("change", function() {
        mysearch.settings.set(mysearchbar.timerange.val());
    });

    // actions for the populate search Buttons
    $('#moviesshortclassic').on("click", function (e){
      mysearchbar.val('| inputlookup movies_short_splunk.csv \n\
| table obj_type, node_ref, node_label, rel_type, rel_src_node, rel_dst_node, prop:* \n\
| sort 0 obj_type, -node_label');
    });

    // actions for the populate search Buttons
    $('#moviesshortjson').on("click", function (e){
      mysearchbar.val('| inputlookup movies_short_splunk.csv \n\
| table obj_type, node_ref, node_label, rel_type, rel_src_node, rel_dst_node, prop:* \n\
| sort 0 obj_type, -node_label');
    });

    // actions for the populate search Buttons
    $('#fwtojson').on("click", function (e){
      mysearchbar.val('| inputlookup graphee_demo_concepts_firewall_traffic.csv \n\
| rex field=dst_ip mode=sed "s/^\d+\\.\d+\\.\d+\\./10.10.10./g" \n\
| search NOT dst_ip = 10.10.10.0 NOT src_ip=0.* \n\
| rename dest_port as dst_port \n\
| table _time, src_ip, src_port, dst_ip, dst_port, bytes_received, bytes_sent, packets_received, packets_sent \n\
``` base data above ``` \n\
\n\
``` get all the fields ready for what we want to see in the graph: Which src ips connect to our hosted systems and services? ``` \n\
``` we have src and dst nodes in this firewall dataset ``` \n\
``` Let\'s say we relate the src ips to dst ips via their connection and tag some intensity properties (count connections, transfered bytes, packets) to this relationship (rel) ``` \n\
``` so we can now reduce the dataset via a |stats to this data ```  \n\
| eval conn_bytes = bytes_received + bytes_sent \n\
| eval conn_packets = packets_received + packets_sent \n\
| stats sum(conn_bytes) as sum_conn_bytes, sum(conn_packets) as sum_conn_packets, count as count_conn by src_ip, dst_ip, dst_port \n\
| eval rel_type = "connects_to" \n\
``` Our sources are the src_ip. We need a key for it. Let it just be the src_ip. That suffices (in regards of uniqueness) for that demo. Our key will go into the field src_node_ref.  \n\
    Neo4j requires us to prefix a variable like node_id with a word char. We use "n" here. And we add a fake hostname, to demo node properties in the json transform below. ``` \n\
| eval src_node_ref = "n" . src_ip \n\
| rex mode=sed field=src_node_ref "s/[\\.\\/:]/_/g"  \n\
| eval src_node_label = "ip" \n\
| eval src_hostname = src_ip . ".example.com" \n\
``` And we have our destination services and need key for them: dst_node_ref. We describe the destination service with the triple dst_ip, dst_port and protocol (this one is not present on the dataset and we fake it below).  \n\
    We alse use "n" to prefix node_id again. And we also add a fake hostname. ``` \n\
| eval dst_proto = "tcp" \n\
| eval dst_node_ref = "n" . dst_ip . ":" . dst_port . "/" . dst_proto \n\
| rex mode=sed field=dst_node_ref "s/[\\.\\/:]/_/g"  \n\
| eval dst_node_label = "service" \n\
| eval dst_hostname = dst_ip . ".internal.local" \n\
\n\
``` With the SPL above we now have all required fields ready for our graph. But those many fields are awkward to handle. Throwing them around, transforming them into a serial stream of nodes and rels is not fun to do or maintain. ``` \n\
``` To solve that, the following approach is proposed: Let us understand our dataset as objects. We have three objects: src and dst nodes and rels. ``` \n\
``` The solution is to zip the fields of on object into a json blob and handle it in that form. We can use the awesome command |tojson (since v8.2.6) and |fromjson (since v9.0.0) Splunk introduced lately to achieve this easily. ``` \n\
| eval obj_type = "node" \n\
``` transform src ``` \n\
| tojson output_field=src_props src_ip, src_hostname \n\
| tojson output_field=src_node obj_type, src_node_ref, src_node_label, src_props \n\
``` transform dst ``` \n\
| tojson output_field=dst_props dst_ip, dst_hostname, dst_port, dst_proto \n\
| tojson output_field=dst_node obj_type, dst_node_ref, dst_node_label, dst_props \n\
``` transform rel ``` \n\
| tojson output_field=rel_props sum_conn_bytes, sum_conn_packets, count_conn \n\
| eval rel_src_node = src_node_ref \n\
| eval rel_dst_node = dst_node_ref \n\
| eval obj_type = "rel" \n\
| tojson output_field=rel obj_type, rel_type, rel_src_node, rel_dst_node, rel_props \n\
| fields src_node, dst_node, rel \n\
      ');
    });


    // Create the search manager
    var mysearch2 = new SearchManager({
      id: "base2",
      autostart: "false",
      app: "search",
      preview: true,
      cache: true,
      status_buckets: 300,
      required_field_list: "*",
      search: ""
    });

    // Create the views
    var mysearchbar2 = new SearchbarView ({
      id: "searchbar2",
      managerid: "base2",
      el: $("#mysearchbar2")
    }).render();

    var mysearchcontrols2 = new SearchControlsView ({
      id: "searchcontrols2",
      managerid: "base2",
      el: $("#mysearchcontrols2")
    }).render();

    // When the query in the searchbar changes, update the search manager
    mysearchbar2.on("change", function() {
      mysearch2.settings.unset("search");
      mysearch2.settings.set("search", mysearchbar2.val());

      // set token value with search string
      var searchString2 = mysearchbar2.val();

      //Collect tokens from the dashboard
      function setToken(name, value) {
        defaultTokenModelun.set(name, value);
        submittedTokenModelun.set(name, value);
      }
      function unsetToken(name) {
        defaultTokenModelun.unset(name);
        submittedTokenModelun.unset(name);
      }
      var defaultTokenModelun = mvc.Components.getInstance('default', { create: true });
      var submittedTokenModelun = mvc.Components.getInstance('submitted', { create: true });

      //Show the edit panel
      setToken("searchString2",searchString2);

      setToken("earliest",mysearch2.settings.attributes.earliest_time);
      setToken("latest",mysearch2.settings.attributes.latest_time);

      console.log("Eariest time: " + defaultTokenModelun.get("earliest"));
      console.log("Latest time: " + defaultTokenModelun.get("latest"));
      //unsetToken("beforeSearch2");
    });

    // When the timerange in the searchbar changes, update the search manager
    mysearchbar2.timerange.on("change", function() {
      mysearch2.settings.set(mysearchbar2.timerange.val());
    });


    $('#transform').on("click", function (e){
      mysearchbar2.val('| inputlookup movies_short_splunk.csv \n\
| table obj_type, node_ref, node_label, rel_type, rel_src_node, rel_dst_node, prop:* \n\
| sort 0 obj_type, -node_label \n\
\n\
| tojson output_field=props prop:* \n\
| rex mode=sed field=props "s/(\\")prop:/\\1/g" \n\
| fields - prop:* \n\
| tojson output_field=json_obj \n\
| fields - obj_type, node_ref, node_label, rel_type, rel_src_node, rel_dst_node, props \n');
    });

    $('#fwlogsjsonexpand').on("click", function (e){
      mysearchbar2.val('| inputlookup graphee_demo_concepts_firewall_traffic.csv \n\
``` start of same code block as in step #1 ``` \n\
| rex field=dst_ip mode=sed "s/^\d+\\.\d+\\.\d+\\./10.10.10./g" \n\
| search NOT dst_ip = 10.10.10.0 NOT src_ip=0.* \n\
| rename dest_port as dst_port \n\
| table _time, src_ip, src_port, dst_ip, dst_port, bytes_received, bytes_sent, packets_received, packets_sent \n\
``` base data above ``` \n\
\n\
``` get all the fields ready for what we want to see in the graph: Which src ips connect to our hosted systems and services? ``` \n\
``` we have src and dst nodes in this firewall dataset ``` \n\
``` Let\'s say we relate the src ips to dst ips via their connection and tag some intensity properties (count connections, transfered bytes, packets) to this relationship (rel) ``` \n\
``` so we can now reduce the dataset via a |stats to this data ```  \n\
| eval conn_bytes = bytes_received + bytes_sent \n\
| eval conn_packets = packets_received + packets_sent \n\
| stats sum(conn_bytes) as sum_conn_bytes, sum(conn_packets) as sum_conn_packets, count as count_conn by src_ip, dst_ip, dst_port \n\
| eval rel_type = "connects_to" \n\
``` Our sources are the src_ip. We need a key for it. Let it just be the src_ip. That suffices (in regards of uniqueness) for that demo. Our key will go into the field src_node_ref.  \n\
    Neo4j requires us to prefix a variable like node_id with a word char. We use "n" here. And we add a fake hostname, to demo node properties in the json transform below. ``` \n\
| eval src_node_ref = "n" . src_ip \n\
| rex mode=sed field=src_node_ref "s/[\\.\\/:]/_/g"  \n\
| eval src_node_label = "ip" \n\
| eval src_hostname = src_ip . ".example.com" \n\
``` And we have our destination services and need key for them: dst_node_ref. We describe the destination service with the triple dst_ip, dst_port and protocol (this one is not present on the dataset and we fake it below).  \n\
    We alse use "n" to prefix node_id again. And we also add a fake hostname. ``` \n\
| eval dst_proto = "tcp" \n\
| eval dst_node_ref = "n" . dst_ip . ":" . dst_port . "/" . dst_proto \n\
| rex mode=sed field=dst_node_ref "s/[\\.\\/:]/_/g"  \n\
| eval dst_node_label = "service" \n\
| eval dst_hostname = dst_ip . ".internal.local" \n\
\n\
``` With the SPL above we now have all required fields ready for our graph. But those many fields are awkward to handle. Throwing them around, transforming them into a serial stream of nodes and rels is not fun to do or maintain. ``` \n\
``` To solve that, the following approach is proposed: Let us understand our dataset as objects. We have three objects: src and dst nodes and rels. ``` \n\
``` The solution is to zip the fields of on object into a json blob and handle it in that form. We can use the awesome command |tojson (since v8.2.6) and |fromjson (since v9.0.0) Splunk introduced lately to achieve this easily. ``` \n\
| eval obj_type = "node" \n\
``` transform src ``` \n\
| tojson output_field=src_props src_ip, src_hostname \n\
| tojson output_field=src_node obj_type, src_node_ref, src_node_label, src_props \n\
``` transform dst ``` \n\
| tojson output_field=dst_props dst_ip, dst_hostname, dst_port, dst_proto \n\
| tojson output_field=dst_node obj_type, dst_node_ref, dst_node_label, dst_props \n\
``` transform rel ``` \n\
| tojson output_field=rel_props sum_conn_bytes, sum_conn_packets, count_conn \n\
| eval rel_src_node = src_node_ref \n\
| eval rel_dst_node = dst_node_ref \n\
| eval obj_type = "rel" \n\
| tojson output_field=rel obj_type, rel_type, rel_src_node, rel_dst_node, rel_props \n\
| fields src_node, dst_node, rel \n\
``` end of same code block as in step #1 ``` \n\
\n\
\n\
``` To transform our multi-column dataset into a flat single-column table we use the following approach:\n\
    We need to expand each line by the number of contained objects. Using |stats is a stable way command for this purpose.\n\
    If we provide the by clause of |stats with multivalue field, it will behave as a duplicator for each event. \n\
    To achieve this, first we uniquely identify each line with a key with the following |streamstats:  ```\n\
| streamstats count as evtId\n\
``` In the duplicator multivalue field we simply put how many objects we have in each line, essentially instructing |stats to create so many duplicates of each line.   ```\n\
| eval expander = mvappend( "src", "dst", "rel" )\n\
``` both evtId, expander are used as by clause for |stats. This will create 3 identical copies of each line. ```\n\
| stats first(src_node) as src_node, first(dst_node) as dst_node, first(rel) as rel by evtId, expander\n\
``` with this most work is done. The multi-column dataset is expanded and can now carry each node and rel on a single line. ```\n\
\n\
``` next we remove the unneeded duplicates.  ```\n\
| eval src_node = if( expander == "src", src_node, null() )\n\
| eval dst_node = if( expander == "dst", dst_node, null() )\n\
| eval rel      = if( expander == "rel", rel,      null() )\n\
``` manually tidy up the field names. This is crude, as there is no SPL command that allows in-json field renames, but practical enough for this demo. ```\n\
| rex mode=sed field=src_node "s/\\"src_/\\"/g"\n\
| rex mode=sed field=dst_node "s/\\"dst_/\\"/g"\n\
| rex mode=sed field=rel      "s/\\"rel_props/\\"props/g"\n\
``` flatten the list into a single column ```\n\
| eval json_obj = coalesce( src_node, dst_node, rel )\n\
| fields - evtId, expander, src_node, dst_node, rel\n\
``` done. we now have an expanded, flattened nodes and rels dataset. ```\n\
\n\
``` use myLimit to create less objects on the neo4j instance and have the command finish faster.```\n\
| streamstats count as evtId\n\
| eval objsPerRow = 3\n\
| eval myLimit = 100\n\
| eval overallLimit = objsPerRow * myLimit\n\
| where evtId <= overallLimit\n\
\n\
``` do not forget that nodes need to be created before rels. this is achieved by sorting nodes to the beginning of the the dataset. otherwise the |creategraph commands error upon trying to create rels for non-existing nodes.  ```\n\
| spath input=json_obj obj_type \n\
| sort 0 obj_type\n\
| fields json_obj\n\
\n\
``` | creategraphjson uri="somehost" account="someaccount" noact=f mode="merge" ```\n\
      ');
    });

});
