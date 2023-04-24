/*
Copyright © 2023 Pavel Tisnovsky

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package main

import (
	"fmt"
	"log"
	"os"

	"github.com/google/uuid"
)

const uniqueClusterNames = 10

func main() {
	// open output file
	fout, err := os.Create("cluster_names.txt")
	if err != nil {
		log.Fatal(err)
	}

	// close fo on exit and check for its returned error
	defer func() {
		err := fout.Close()

		if err != nil {
			log.Fatal(err)
		}
	}()

	for i := 0; i < uniqueClusterNames; i++ {
		clusterName := uuid.New().String()
		log.Print(clusterName)
		fmt.Fprintf(fout, "%s\n", clusterName)
	}
}
