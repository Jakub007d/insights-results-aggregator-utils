#!/usr/bin/env python3

# Copyright © 2021 Pavel Tisnovsky
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

"""Script to retrieve results from the external data pipeline through the standard REST API.

Description
-----

This script can be used to perform several operations with external data
pipeline usually deployed on Stage environment and accessible through proxy
server.

First operation retrieves list of clusters from the external data pipeline
through the standard REST API (and optionally via proxy server). Organization
ID needs to be provided via CLI option, because list of clusters is filtered by
organization. This operation is selected by using `-l` command line option.

Second operation retrieves results from the external data pipeline for several
clusters. List of clusters needs to be stored in a plain text file. Name of
this text file is to be provided by `-i` command line option. This operation is
selected by using `-r` command line option.

Third operation compares two sets of results. Each set needs to be stored in
separate directory. CSV file with detailed comparison of such two sets is
generated during this operation. This operation is selected by using `-c`
command line option.

REST API on Stage environment is accessed through proxy. Proxy name should be
provided via CLI together with user name and password used for basic auth.

Usage
-----

```
st.py [-h] [-a ADDRESS] [-x PROXY] [-u USER] [-p PASSWORD]
           [-o ORGANIZATION] [-l] [-r] [-i INPUT] [-c]
           [-d1 DIRECTORY1] [-d2 DIRECTORY2]
           [-e EXPORT_FILE_NAME] [-d] [-v]

optional arguments:
  -h, --help            show this help message and exit
  -l, --cluster-list    Operation to retrieve list of clusters via REST API
  -r, --retrieve-results
                        Retrieve results for given list of clusters via REST
                        API
  -c, --compare-results Compare two sets of results, each set stored in its
                        own directory
  -a ADDRESS, --address ADDRESS
                        Address of REST API for external data pipeline
  -x PROXY, --proxy PROXY
                        Proxy to be used to access REST API
  -u USER, --user USER  User name for basic authentication
  -p PASSWORD, --password PASSWORD
                        Password for basic authentication
  -o ORGANIZATION, --organization ORGANIZATION
                        Organization ID
  -i INPUT, --input INPUT
                        Specification of input file (with list of clusters,
                        for example)
  -d1 DIRECTORY1, --directory1 DIRECTORY1
                        First directory containing set of results
  -d2 DIRECTORY2, --directory2 DIRECTORY2
                        Second directory containing set of results
  -e EXPORT, --export EXPORT
                        Name of CSV file with exported comparison results
  -d, --additional-info
                        Add additional info about data pipeline components
                        into CSV report
  -v, --verbose         Make messages verbose

please note that at at least one operation needs to be specified:
  -l, --cluster-list
  -r, --retrieve-results
  -c, --compare-results
```

Examples
-----

* Retrieve list of clusters via REST API for organization ID 12345678

```
st.py -l -a https://$REST_API_URL -x http://$PROXY_URL -u $USER_NAME -p $PASSWORD -o 12345678
```

* Read results for clusters whose IDs are stored in file named `clusters.txt`

```
st.py -r -a https://$REST_API_URL -x http://$PROXY_URL -u $USER_NAME -p $PASSWORD -i clusters.txt
```

* Compare results stored in directories `c1` and `c`

```
st.py -c -d1=c1 -d2=c2 -a https://$REST_API_URL -x http://$PROXY_URL -u $USER_NAME -p $PASSWORD
```

Generated documentation in literate programming style
-----
<https://redhatinsights.github.io/insights-results-aggregator-utils/packages/st.html>
"""


import requests
import json
import sys
import os
import csv

from datetime import datetime
from argparse import ArgumentParser


def cli_arguments():
    """Retrieve all CLI arguments provided by user."""
    # First of all, we need to specify all command line flags that are
    # recognized by this tool.
    parser = ArgumentParser()

    # All supported command line arguments and flags
    parser.add_argument("-a", "--address", dest="address", required=False,
                        help="Address of REST API for external data pipeline")

    parser.add_argument("-x", "--proxy", dest="proxy", required=False,
                        help="Proxy to be used to access REST API")

    parser.add_argument("-u", "--user", dest="user", required=False,
                        help="User name for basic authentication")

    parser.add_argument("-p", "--password", dest="password", required=False,
                        help="Password for basic authentication")

    parser.add_argument("-o", "--organization", dest="organization", required=False,
                        help="Organization ID")

    parser.add_argument("-l", "--cluster-list", dest="cluster_list", action="store_true",
                        help="Operation to retrieve list of clusters via REST API",
                        default=None)

    parser.add_argument("-r", "--retrieve-results", dest="retrieve_results", action="store_true",
                        help="Retrieve results for given list of clusters via REST API",
                        default=None)

    parser.add_argument("-i", "--input", dest="input", default=None, required=False,
                        help="Specification of input file (with list of clusters, for example)")

    parser.add_argument("-c", "--compare-results", dest="compare_results", action="store_true",
                        default=None, required=False,
                        help="Compare two sets of results, each set stored in its own directory")

    parser.add_argument("-d1", "--directory1", dest="directory1", required=False, default=None,
                        help="First directory containing set of results")

    parser.add_argument("-d2", "--directory2", dest="directory2", required=False, default=None,
                        help="Second directory containing set of results")

    parser.add_argument("-e", "--export", dest="export_file_name", required=False,
                        default="report.csv",
                        help="Name of CSV file with exported comparison results")

    parser.add_argument("-d", "--additional-info", dest="additional_info", action="store_true",
                        default=None, required=False,
                        help="Add additional info about data pipeline components into CSV report")

    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true", default=None,
                        help="Make messages verbose", required=False)

    # Now it is time to parse flags, check the actual content of command line
    # and fill-in the object named `args`.
    return parser.parse_args()


def main():
    """Entry point to this script."""
    # Parse and process and command line arguments.
    args = cli_arguments()

    # Verbosity flag
    verbose = args.verbose

    # setup proxy or proxies
    proxies = {
       'https': args.proxy
    }

    if verbose:
        print("Proxy settings:", proxies)

    # tuple with items needed to be filled for basic authentication
    auth = (args.user, args.password)

    if verbose:
        print("Auth settings:", auth)

    if not any((args.cluster_list, args.retrieve_results, args.compare_results)):
        print("No action requested, add -l, -r, or -c")
        sys.exit(1)

    if args.cluster_list:
        retrieve_cluster_list(args.organization, args.address, proxies, auth, verbose)

    if args.retrieve_results:
        retrieve_results(args.address, proxies, auth, args.input, verbose)

    if args.compare_results:
        assert args.directory1 is not None, \
            "-d1/--directory1 CLI option needs to be provided in order to compare results"
        assert args.directory2 is not None, \
            "-d2/--directory2 CLI option needs to be provided in order to compare results"

        # retrieve and use additional info about pipeline if user depands to
        info = None
        if args.additional_info:
            info = retrieve_additional_info(args.address, proxies, auth, verbose)

        compare_results(args.directory1, args.directory2, args.export_file_name, info)


def call_rest_api(url, proxies, auth):
    """Call REST API, retrieve payload, and unmarshal it from JSON."""
    # send request to REST API
    response = requests.get(url, proxies=proxies, auth=auth)

    # elementary check for response content
    assert response is not None, "Proper response expected"
    assert response.status_code == requests.codes.ok, \
        f"Unexpected HTTP code returned: {response.status_code}"

    # response should be in JSON format, time to parse it
    payload = response.json()
    assert payload is not None, "JSON response expected"

    return payload


def retrieve_cluster_list(organization, address, proxies, auth, verbose):
    """Retrieve list of clusters from the external data pipeline REST API endpoint."""
    # construct URL to get list of clusters for given organization ID
    url = f'{address}/v1/organizations/{organization}/clusters'

    if verbose:
        print("URL to access:", url)

    payload = call_rest_api(url, proxies, auth)

    # check the payload content
    assert "status" in payload, "'status' field needs to be present in the payload"
    assert "clusters" in payload, "'clusters' field needs to be present in the payload"

    # print list of clusters to standard output
    clusters = sorted(payload["clusters"])
    for cluster in clusters:
        print(cluster)


def retrieve_results(address, proxies, auth, input_file, verbose):
    """Retrieve results from the external data pipeline REST API endpoint."""
    errors = {}

    # input file containing list of clusters
    with open(input_file, "r") as input_file:
        # iterate over all cluster names
        for line in input_file:
            cluster = line.strip()

            if verbose:
                print("Cluster: ", cluster)

            # construct URL to get report for one specified cluster
            url = f'{address}/v1/clusters/{cluster}/report'

            if verbose:
                print("URL to access:", url)

            try:
                # try to retrieve results for given cluster
                retrieve_results_for_cluster(url, proxies, auth, cluster, verbose)
            except Exception as e:
                # store error to be used later
                errors[cluster] = e

    display_errors(errors)


def retrieve_additional_info(address, proxies, auth, verbose):
    """Retrieve additional info about the external data pipeline via REST API endpoint."""
    # construct URL to get info from pipeline
    url = f'{address}/v1/info'

    if verbose:
        print("URL to access:", url)

    # try to access /info endpoint, if it fails, it fails, that's ok -> the
    # pipeline is doomed anyway in this case
    payload = call_rest_api(url, proxies, auth)

    return payload["info"]


def display_errors(errors):
    """Display all errors or exceptions thrown during the selected operation."""
    print("-"*60)

    if len(errors) > 0:
        print("Errors detected during results processing")
        for cluster, e in errors.items():
            print(cluster, repr(e))
    else:
        print("No errors found")

    print("-"*60)


def retrieve_results_for_cluster(url, proxies, auth, cluster, verbose):
    """Retrieve results for one specified cluster and store it into the file."""
    payload = call_rest_api(url, proxies, auth)

    # check the payload content
    assert "status" in payload, "'status' field needs to be present in the payload"

    # pretty print the output
    results = json.dumps(payload, indent=4)

    filename = "{}.json".format(cluster)

    # generate output file with cluster results
    with open(filename, "w") as json_file:
        json_file.write(results)


def compare_results(directory1, directory2, filename, info):
    """Compare results stored in two different directories."""
    files1 = set(read_list_of_clusters_from_directory(directory1))
    files2 = set(read_list_of_clusters_from_directory(directory2))

    # common cluster names in both directories
    common = files1 & files2

    # reduntant results
    redundant_d1 = sorted(list(files1 - common))
    redundant_d2 = sorted(list(files2 - common))

    # compute difference in results
    comparison_results = compare_results_sets(directory1, directory2, common)

    # create a new CSV file with detailed report of differences between two
    # sets of results
    with open(filename, "w") as csvfile:
        # create a CSV writer object
        csv_writer = csv.writer(csvfile, quotechar='"', quoting=csv.QUOTE_ALL)
        assert csv_writer is not None, "CSV writer can not be constructed"

        # export all required information into CSV file
        export_additional_info(csv_writer, info)
        export_basic_info(csv_writer, directory1, directory2, files1, files2, common)

        export_redundant_clusters(csv_writer, redundant_d1, "Redundand clusters in 1st directory")
        export_redundant_clusters(csv_writer, redundant_d2, "Redundand clusters in 2nd directory")

        export_comparison_results(csv_writer, comparison_results)


def compare_results_sets(directory1, directory2, common):
    """Compare two results sets."""
    diff_results = []
    rule_ids = {}

    # iterate over all clusters
    for cluster in sorted(common):
        diff = {}
        diff["cluster"] = cluster

        try:
            # preliminary - can be changed later in exception handler
            diff["status"] = "ok"
            diff["error"] = ""

            # not true yet!
            diff["same_results"] = "yes"  # not true yet

            # try to read both results to be compared
            r1 = read_cluster_results(directory1, cluster)
            r2 = read_cluster_results(directory2, cluster)

            # 1st step is simple: rule hits counters comparison as exposed in
            # metadata field in JSON
            d1 = compare_rule_hits_count(r1, r2, diff)

            # rule hit numbers are the same, let's continue with 2nd step
            if d1:
                # TODO: better comparison
                d2 = compare_rule_hits(r1, r2, diff)
                if d2:
                    pass
                else:
                    diff["same_results"] = "no"
            else:
                # now we know for sure, that rule hit counters are different
                diff["same_results"] = "no"
                diff["same_hits"] = "?"

        except Exception as e:
            # fill-in info about error that occured during results reading or
            # during comparison
            diff["status"] = "error"
            diff["error"] = repr(e)

        # update diff results
        diff_results.append(diff)

    return diff_results


def compare_rule_hits_count(r1, r2, diff):
    """Just compare rule hits metadata and fill-in diff structure accordingly."""
    hits1 = r1["report"]["meta"]["count"]
    hits2 = r2["report"]["meta"]["count"]

    # remember counters -> needs to be written into the table
    diff["hits1"] = hits1
    diff["hits2"] = hits2

    the_same = hits1 == hits2

    # result of comparison of two counters
    diff["eq_hits"] = "yes" if the_same else "no"

    # return comparison result
    return the_same


def compare_rule_hits(r1, r2, diff):
    """Compare 'read' rule hits and fill-in diff structure accordingly."""
    d1 = r1["report"]["data"]
    d2 = r2["report"]["data"]

    all_found = True

    for hit1 in d1:
        found = False
        for hit2 in d2:
            if hit1["rule_id"] == hit2["rule_id"]:
                found = True
        if not found:
            all_found = False

    # result of comparison
    diff["same_hits"] = "yes" if all_found else "no"

    # return comparison result
    return all_found


def read_cluster_results(directory, cluster):
    """Try to read results for given cluster, where results are stored in specified directory."""
    filename = f"{directory}/{cluster}.json"

    with open(filename, "r") as fin:
        raw_data = fin.read()
        results = json.loads(raw_data)

    return results


def read_list_of_clusters_from_directory(directory):
    """Read list of clusters (taken from file names) from given directory."""
    # list of all files in directory
    files = os.listdir(directory)
    # filter just JSON files and get rid of file extension
    return [f[:-5] for f in files if f.endswith(".json")]


def export_additional_info(csv_writer, info):
    """Export additional info about pipeline components."""
    if info is None:
        return

    csv_writer.writerow(("External data pipeline components",))

    csv_writer.writerow(("", "Smart Proxy"))
    export_dictionary(csv_writer, info["SmartProxy"])

    csv_writer.writerow(("", "Content Service"))
    export_dictionary(csv_writer, info["ContentService"])

    csv_writer.writerow(("", "Insights Results Aggregator"))
    export_dictionary(csv_writer, info["Aggregator"])

    # empty row
    csv_writer.writerow(())


def export_dictionary(csv_writer, dictionary):
    """Export content of given dictionary into CSV (starting at third row)."""
    for key in sorted(dictionary.keys()):
        csv_writer.writerow(("", "", key, dictionary[key]))


def export_basic_info(csv_writer, directory1, directory2, files1, files2, common):
    """Export basic info into CSV file."""
    csv_writer.writerow(("Basic info about test results",))
    csv_writer.writerow(("", "Tested on", datetime.now().isoformat().replace("T", " ")))
    csv_writer.writerow(("", "1st directory with results", directory1))
    csv_writer.writerow(("", "2nd directory with results", directory2))
    csv_writer.writerow(("", "Results in 1st directory", len(files1)))
    csv_writer.writerow(("", "Results in 2nd directory", len(files2)))
    csv_writer.writerow(("", "Common clusters to compare", len(common)))

    # empty row
    csv_writer.writerow(())


def export_redundant_clusters(csv_writer, files, title):
    """Export list of redundant clusters into CSV."""
    csv_writer.writerow((title,))
    csv_writer.writerow(("n", "cluster"))

    # write all cluster names preceded by counter
    for i, cluster in enumerate(files):
        csv_writer.writerow((i, cluster))

    # empty row
    csv_writer.writerow(())


def export_comparison_results(csv_writer, comparison_results):
    csv_writer.writerow(("Comparison results",))
    csv_writer.writerow(("n", "cluster", "status", "same results", "eq.#hits", "hits1", "hits2",
                         "same hits", "error"))

    # write all cluster names preceded by counter
    for i, r in enumerate(comparison_results):
        if r["status"] == "ok":
            csv_writer.writerow((i, r["cluster"], r["status"], r["same_results"],
                                 r["eq_hits"], r["hits1"], r["hits2"], r["same_hits"],
                                 r["error"]))
        else:
            csv_writer.writerow((i, r["cluster"], r["status"], "", "", "", "", "", r["error"]))


# If this script is started from command line, run the `main` function which is
# entry point to the processing.
if __name__ == "__main__":
    main()
