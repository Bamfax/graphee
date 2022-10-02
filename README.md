# GRAPH-E
A Neo4j(r) connector for Splunk(r) (using Cypher)

Persist your Splunk data into Neo4j graphs, query your Neo4j data from Splunk and execute custom cypher commands from Splunk SPL. All work on Neo4j is done via Cypher using the Neo4j Python driver.
<br/><br/>
This app started out as a freetime project so I could learn Python, Neo4j and to get Splunk more connected to the Graph side of life. It is currently a playground which aims to find a good workflow for integrating Splunk and Neo4j. Therefore the codebase will still change a lot in the potential future life of this app. It may evolve into a more general Splunk to Cypher connector (connecting different Graph DBs), it may also try to help out even more with graph topics in Splunk. For more graph things be sure to check out the great apps mentioned under "More Splunk Graph Apps" below.
<br/><br/>
Disclaimer:This app comes without any warranty. Check the code before you use it. Use at your own risk.

All trademarks are property of their respective owners.

<br/><br/>
<br/><br/>
<br/><br/>
<br/><br/>

Why the name? Because we need a Graph helper out there.
- After 700 years of doing what he was built for - he'll discover what he's meant for.

<br/><br/>

## More Splunk Graph Apps
Be sure to check these Splunk Apps out, as they bring even more Graph life into Splunk:
- 3D Graph Network Topology Visualization
    - https://splunkbase.splunk.com/app/4611
    - https://github.com/splunk/splunk-3D-graph-network-topology-viz
    - Awesome, large scale, GPU-accelerated Graph Visualization
    - Also includes NetworkX bindings (bundled in Slunk PSC)
    - Based upon the awesome underlying library https://github.com/vasturiano/3d-force-graph
- Graphviz:
    - https://splunkbase.splunk.com/app/4346
    - https://github.com/ThomasDancoisne/SA-Graphviz
    - Very customizable and interactable Graph Visualization
- Python for Scientific Computing (PSC)
    - https://github.com/splunk/Splunk-python-for-scientific-computing
    - Linux 64-bit: https://splunkbase.splunk.com/app/2882/
    - Windows 64-bit: https://splunkbase.splunk.com/app/2883/
    - Contains NetworkX library and allows binding to it (via interface API)

<br/><br/>

## License

This app, excluding the bundled python modules, are licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details. 

<br/><br/>

## Included python modules

The bundled python modules are independent works which come with their own license. Please refer to their website for current and detailed information regarding their license.

As of 02-10-2022, the following software is included in this app:
### Certifi 
- v2022.9.24
- https://github.com/certifi/python-certifi
    - Certifi@Github, 31 contributors
    - License: Github URI mentions no specific license for certifi itself
- https://pypi.org/project/certifi/
    - Author: Kenneth Reitz
    - License: Mozilla Public License 2.0 (MPL 2.0) (MPL-2.0)

### charset-normalizer
- v2.1.1
- https://github.com/ousret/charset_normalizer
    - Author: Ousret@Github, TAHRI Ahmed R., 15 contributors
    - License: MIT license
- https://pypi.org/project/charset-normalizer/
    - Author: Ahmed TAHRI @Ousret
    - License: MIT License (MIT)

### defusedxml
- v0.7.1
- https://github.com/tiran/defusedxml
    - Author: tiran, Christian Heimes, 8 contributors
    - License: Python Software Foundation License Version 2
- https://pypi.org/project/defusedxml/
    - Author: Christian Heimes
    - Python Software Foundation License (PSFL)

### idna
- v3.4
- https://github.com/kjd/idna
    - Author: kjd@Github, Kim Davies, 18 contributors
    - License: BSD-3-Clause 
- https://pypi.org/project/idna/
    - Author: Kim Davies
    - License: BSD License

### neo4j
- v5.0.1
- https://github.com/neo4j/neo4j-python-driver
    - Author: neo4j@Github, Neo4j, Inc., 29 contributors
    - License: Apache-2.0 license 
- https://pypi.org/project/neo4j/
    - Author: Neo4j, Inc.
    - License: Apache Software License (Apache License, Version 2.0)

### PySocks
- v1.7.1
- https://github.com/Anorov/PySocks
    - Author: Anorov@Github, 29 contributors
    - License: https://github.com/Anorov/PySocks/blob/master/LICENSE
- https://pypi.org/project/PySocks/
    - Author: Anorov
    - License: BSD

### pytz
- v2022.2.1
- https://pythonhosted.org/pytz/
    - Author: Stuart Bishop
    - License: MIT license
- https://pypi.org/project/pytz/
    - Author: Stuart Bishop
    - License: MIT License (MIT)

### requests
- v2.28.1
- https://github.com/psf/requests
    - Author: Python Software Foundation, 613 contributors
    - License: Apache-2.0 license 
- https://pypi.org/project/requests/
    - Author: Kenneth Reitz
    - License: Apache Software License (Apache 2.0)

### splunk-3D-graph-network-topology-viz
- Including partly derivate work of it.
- v1.3.2
- https://github.com/splunk/splunk-3D-graph-network-topology-viz
    - Author: Splunk@Github, Splunk Inc., 4 contributors
    - License: Apache-2.0 license

### solnlib
- v4.7.0
- https://github.com/splunk/addonfactory-solutions-library-python
    - Author: Splunk@Github, Splunk Inc., 37 contributors
    - License: Apache-2.0 license
- https://pypi.org/project/solnlib/
    - Author: Splunk
    - License: Apache Software License (Apache-2.0)

### sortedcontainers
- v2.4.0
- https://github.com/grantjenks/python-sortedcontainers
    - Author: grantjenks@Github, Grant Jenks, 21 contributors
    - License: Apache Software License (Apache-2.0)
- https://pypi.org/project/sortedcontainers/
    - Author: Grant Jenks
    - License: Apache Software License (Apache-2.0)

### splunk_sdk
- v1.7.2
- https://github.com/splunk/splunk-sdk-python
    - Author: Splunk@Github, Splunk Inc., 71 contributors
    - License: Apache-2.0 license
- https://pypi.org/project/splunk-sdk/
    - Author: Splunk
    - License: Apache Software License (Apache-2.0)

### splunklib
- Part of Splunk SDK for Python

### splunktalib
- v3.0.1
- https://github.com/splunk/addonfactory-ta-library-python
    - Author: Splunk@Github, Splunk Inc., 14 contributors
    - License: Apache Software License (Apache-2.0)
- https://pypi.org/project/splunktalib/
    - Author: rfaircloth-splunk
    - License: Apache Software License (Apache-2.0)

### splunktaucclib
- v6.0.6
- https://github.com/splunk/addonfactory-ucc-library
    - Author: Splunk@Github, Splunk Inc., 14 contributors
    - License: Apache-2.0 license
- https://pypi.org/project/splunktaucclib/
    - Author: Splunk
    - License: Apache Software License (Apache-2.0)

### testkitbackend
- Part of Neo4j Python Driver

### urllib3
- v1.26.12
- https://github.com/urllib3/urllib3
    - Author: urllib3@Github, Andrey Petrov, 274 contributors
    - License: MIT license
- https://pypi.org/project/urllib3/
    - Author: Andrey Petrov
    - License: MIT License (MIT)

### socks.py
- Part of PySocks

### sockshandler.py
- Part of PySocks
