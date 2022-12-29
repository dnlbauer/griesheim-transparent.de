#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

for f in synonyms.txt schema.xml solrconfig.xml; do
  docker cp $SCRIPT_DIR/../solr/configsets/ris/conf/$f griesheimtransparent-solr:/var/solr/data/ris/conf/$f
done
