# Translation Unit

- Source File: `src/questions/11-data-preservation.html.j2`
- Wrapper Name: `__tr_block_0001`
- Wrapper Order: `2`
- Wrapper Key: `we-plan-to-produce-the-following-datasets-no-bcabb3129d`
- Unit Key: `not-published-will-be-published-1f8945296a`
- Source Hash: `d339eb016fb088066b1c3f4d1ad3e3950eebf253`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
(not published) / (will be published)
```

### Source (en)

~~~jinja
{# If will be published #}
          {%- set isPublishedDataPath = [pathPrefix, uuids.isPublishedDataQUuid]|reply_path -%}
          {%- set isPublishedDataAUuid = repliesMap[isPublishedDataPath]|reply_str_value -%}
          {% if isPublishedDataAUuid == uuids.isPublishedDataNoAUuid %}
            (not published)
          {% elif isPublishedDataAUuid == uuids.isPublishedDataYesAUuid %}
            (will be published)
          {% endif -%}
          {# How long will be stored + Metadata FAIRness #}
          {%- set publishedDataHowLongPath = [pathPrefix, uuids.publishedDataHowLongQUuid]|reply_path -%}
          {%- set publishedDataHowLongAUuid = repliesMap[publishedDataHowLongPath]|reply_str_value -%}
          {%- set publishedDataMetadataPersistentPath = [pathPrefix, uuids.publishedDataMetadataPersistentQUuid]|reply_path -%}
          {%- set publishedDataMetadataPersistentAUuid = repliesMap[publishedDataMetadataPersistentPath]|reply_str_value -%}
          {%- if publishedDataHowLongAUuid or (publishedDataMetadataPersistentAUuid == uuids.publishedDataMetadataPersistentYesAUuid) %}
            {% if publishedDataHowLongAUuid == uuids.publishedDataHowLongTechnicalAUuid -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
