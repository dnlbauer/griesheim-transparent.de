FROM solr:9.0.0

# add configset to image
COPY configsets/ris /ris_config

# add additional libs to image
USER root
COPY libs /libs
RUN chown -R solr:solr /libs

USER solr

# create core from configset inside this image and store data in a mounted dir
# on host, prepare data folder and mount to /var/solr
# run: mkdir solr_data; chown 8983:8983 solr_data
# docker run -v $PWD/solr_data://var/solr
CMD ["solr-precreate", "ris", "/ris_config"]
