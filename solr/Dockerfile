FROM solr:9.0.0

COPY configsets/ris /ris_config

USER root
COPY libs /libs

RUN chown -R solr:solr /libs

USER solr

CMD ["solr-precreate", "ris", "/ris_config"]
