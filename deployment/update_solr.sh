#!/bin/bash

for f in synonyms.txt schema.xml solrconfig.xml; do
  docker cp $1/configsets/ris/conf/$f gt-solr:/var/solr/data/ris/conf/$f
done
