#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright © 2021 Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Script to simulate user actions done on OCM UI through the standard REST API.

Description
-----

This script can be used to simulate user actions available on OCM UI related
with recommendations. It interacts with the external data pipeline on Stage
environment.

For a given organization and cluster, the tool allows to simulate the
following operations:
- vote for a rule
- enable a rule
- disable a rule
- disable a rule then enable it

REST API on Stage environment is accessed through proxy. Proxy name should be
provided via CLI together with user name and password used for basic auth.

Usage
-----

``` usage: ui_actions.py [-h] -a ADDRESS [-x PROXY] [-u USER] [-p PASSWORD] -c CLUSTER [-l
CLUSTER_LIST_FILE] [-r RECOMMENDATION] [-e OPERATION [OPERATION ...]] [-v]

optional arguments:
  -h, --help            show this help message and exit
  -a ADDRESS, --address ADDRESS
                        Address of REST API for external data pipeline
  -x PROXY, --proxy PROXY
                        Proxy to be used to access REST API
  -u USER, --user USER  User name for basic authentication
  -p PASSWORD, --password PASSWORD
                        Password for basic authentication
  -c CLUSTER_UUID, --cluster CLUSTER_UUID
                        UUID of the cluster to interact with
  -l FILE, --cluster-list FILE
                        File containing list of clusters to interact with
                        (1 or more cluster uuid expected)
  -s SELECTOR, --rule-selector SELECTOR
                        Recommendation we want to operate upon (RULE_ID|EK format)
  -e OPERATION [OPERATION ...], --execute OPERATION [OPERATION ...]
                        Operation(s) to perform on the provided recommendation.
                        Accepted operations are:
                          - "like"
                          - "dislike"
                          - "reset_vote"
                          - "enable"
                          - "disable"
                          - "disable_feedback [<feedback string>]"
    -v, --verbose       Make execution more verbose

Notes:

- The following arguments need to be specified:
  -a, --addr
  -s, --rule-selector
  -e, --execute
  EITHER -c, --cluster OR -l, --cluster-list

- The file provided to --cluster-list should contain space and/or
linebreak separated UUIDs.

- The --execute argument accepts multiple operations, that would be
executed sequentially in the given order. Each operation is expected
to be provided once.
```

Examples
-----

* Thumbs up vote for a given recommendation

``` ui_actions.py -a 'https://$REST_API_URL' -c '$CLUSTER_ID' -v \
-s 'some.valid.rule_id|ERROR_KEY' -e like -u '$USER' \
-p '$PASSWORD' ```

* Disable a given recommendation

``` ui_actions.py -a 'https://$REST_API_URL' -c '$CLUSTER_ID' -v \
-s 'some.valid.rule_id|ERROR_KEY' -e disable -u '$USER' -p '$PASSWORD' ```


* Disable a given recommendation with feedback

``` ui_actions.py -a 'https://$REST_API_URL' -c '$CLUSTER_ID' -v |
-s 'some.valid.rule_id|ERROR_KEY' -e disable_feedback "some feedback" \
-u '$USER' -p '$PASSWORD' ```

* Execute multiple actions for a given recommendation

``` ui_actions.py -a 'https://$REST_API_URL' -c '$CLUSTER_ID' -v \
-s 'some.valid.rule_id|ERROR_KEY' -e disable_feedback 'some feedback' \
enable dislike -u '$USER' -p '$PASSWORD' ```

``` ui_actions.py -a 'https://$REST_API_URL' -c '$CLUSTER_ID' -v \
-s 'some.valid.rule_id|ERROR_KEY' -e disable_feedback enable \
dislike -u '$USER' -p '$PASSWORD' ```

Note: disable_feedback expects a feedback message (string),
and if none is provided, rule is disabled and no feedback is sent.

Generated documentation in literate programming style
-----
<https://redhatinsights.github.io/insights-results-aggregator-utils/packages/ui_actions.html>
"""

from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
import requests

import re
import sys

ALLOWED_OPERATIONS = {
    "like",
    "dislike",
    "reset_vote",
    "enable",
    "disable",
    "disable_feedback"
}

REGISTERED_OPERATIONS = {}


def register_operation(op, func, data=None):
    print(f"{sys.argv[0]}: info: registering {op}", f"with data: {data}" if data else "")
    REGISTERED_OPERATIONS.update(
        {op: [func, data]}
    )


def cli_arguments():
    """Retrieve all CLI arguments provided by user."""
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)

    parser.add_argument("-a", "--address", dest="addr", required=True,
                        help="Address of REST API for external data pipeline")

    parser.add_argument("-x", "--proxy", dest="proxy", required=False,
                        help="Proxy to be used to access REST API")

    parser.add_argument("-u", "--user", dest="user", required=False,
                        help="User name for basic authentication")

    parser.add_argument("-p", "--password", dest="password", required=False,
                        help="Password for basic authentication")

    parser.add_argument("-o", "--organization", dest="organization",
                        help="ID of the organization to interact with")

    parser.add_argument("-c", "--cluster", dest="cluster",
                        required=not ({'-l', '--cluster-list'} & set(sys.argv)),
                        help="UUID of the cluster to interact with")

    parser.add_argument("-l", "--cluster-list", dest="cluster_list_file",
                        required=not ({'-c', '--cluster'} & set(sys.argv)),
                        help="File containing list of clusters to interact with "\
                            "(1 or more cluster uuid expected)")

    parser.add_argument("-s", "--rule-selector", dest="selector",
                        help="Recommendation we want to operate upon (RULE_ID|EK format)")

    help_message_execute_op = """Operation(s) to perform on the provided recommendation.
    Accepted operations are:
      - "like"
      - "dislike"
      - "reset_vote"
      - "enable"
      - "disable"
      - "disable_feedback [<feedback string>]"
    """
    parser.add_argument("-e", "--execute", dest="operations", action='append', nargs='+',
                        help=help_message_execute_op, required=True)

    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=None,
                        help="Make messages verbose", required=False)

    return parser.parse_args()


def check_api_response(response):
    assert response is not None, "Proper response expected"
    assert response.status_code == requests.codes.ok, \
        "Received {response.status_code} when {requests.codes.ok} expected "


def print_url(url, rest_op, data):
    print("\t", f"Operation: {rest_op}", url, f"{data}" if data else "")


def execute_operations(addr, proxies, auth, clusters, rule_id, error_key):
    for cluster in clusters:
        for action, ops in REGISTERED_OPERATIONS.items():
            url = f"{addr}clusters/{cluster}/rules/{rule_id}.report/error_key/{error_key}/{action}"
            print_url(url, ops[0].__name__, ops[1])
            if ops[1]:
                check_api_response(ops[0](
                    url, proxies=proxies, auth=auth, json=ops[1]))
            else:
                check_api_response(ops[0](
                    url, proxies=proxies, auth=auth))


def main():
    """Entry point to this script."""
    # Parse and process and command line arguments.
    args = cli_arguments()

    # check -c and -l args are not both provided
    if args.cluster and args.cluster_list_file:
        print(f"{sys.argv[0]}: "
              f"error: Please provide cluster UUID through either -c or -l, not both.")
        sys.exit(1)

    # validate the recommendation to work with
    selector = args.selector
    """
    Match any string that has alphanumeric characters separated by at least one dot
    (".") before a vertical line ("|"), followed by only uppercase characters,
    numbers, or underscores ("_")
    """
    if not re.match(r'[a-zA-Z_0-9]+\.[a-zA-Z_0-9.]+\|[A-Z_0-9]+$', selector):
        print(f"{sys.argv[0]}: error: Please provide a valid rule selector (rule_id|ek)")
        sys.exit(1)

    # validate operation(s) to execute
    operations = args.operations[0]
    for op in operations:
        if op in ALLOWED_OPERATIONS:
            if op == "disable_feedback":
                register_operation("disable", requests.put)
                register_operation("disable_feedback", requests.post)
            else:
                register_operation(op, requests.put)
        else:
            # Only OK if it is the feedback for disable_feedback
            if not ("disable_feedback" in REGISTERED_OPERATIONS
                    and REGISTERED_OPERATIONS["disable_feedback"][1] is None):
                print(f"{sys.argv[0]}: error: Received operation: {op}.")
                print(f"{sys.argv[0]}: error: Expected one of {ALLOWED_OPERATIONS}.")
                print(f"{sys.argv[0]}: error: Please provide a valid operation.")
                sys.exit(1)
            else:
                register_operation("disable_feedback", requests.post, {"message": op})

    verbose = args.verbose
    proxies = {
        'https': args.proxy
    } if args.proxy else None
    auth = (args.user, args.password)
    clusters = {args.cluster} if args.cluster else set(open(args.cluster_list_file).read().split())
    rule_id = selector.split("|")[0]
    error_key = selector.split("|")[1]

    if verbose:
        print("Proxy settings:", proxies)
        print("Auth settings:", auth)
        print("Address:", args.addr)
        print("Cluster(s):", clusters)
        print("Rule selector:", selector)
        print("Rule ID:", rule_id)
        print("Error Key:", error_key)
        print("Operations:", REGISTERED_OPERATIONS)

    execute_operations(args.addr, proxies, auth, clusters, rule_id, error_key)


# If this script is started from command line, run the `main` function which is
# entry point to the processing.
if __name__ == "__main__":
    main()
