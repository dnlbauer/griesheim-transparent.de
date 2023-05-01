#!/bin/bash

for f in synonyms.txt schema.xml solrconfig.xml; do
  docker cp $1/configsets/ris/conf/$f griesheimtransparent-solr:/var/solr/data/ris/conf/$f
done
