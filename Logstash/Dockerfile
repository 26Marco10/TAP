FROM docker.elastic.co/logstash/logstash:8.13.4

# delete default configuration
RUN rm -f /usr/share/logstash/pipeline/logstash.conf
RUN bin/logstash-plugin install logstash-integration-kafka

# Copia i file di configurazione nella directory appropriata di Logstash
COPY pipeline.conf /usr/share/logstash/pipeline/
COPY logstash.yml /usr/share/logstash/config/



