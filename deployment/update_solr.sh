#!/bin/bash
# Usage: ./update_solr.sh /path/to/project solr_container_name

for f in synonyms.txt schema.xml solrconfig.xml; do
  docker cp $1/configsets/ris/conf/$f $2:/var/solr/data/ris/conf/$f
done
