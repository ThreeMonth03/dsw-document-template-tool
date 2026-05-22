# Translation Unit

- Source File: `src/questions/10-share-restrictions.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `no-name-given-not-published-will-be-published-d19a5e386b`
- Unit Key: `not-published-will-be-published-e508b7cc7f`
- Source Hash: `f92b1b36ebacb3291ccba4096045d15d7ca7a623`
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
                {# Identifiers #}
                {% set identifiersPath = [pathPrefix, uuids.producedDataIdentifiersQUuid]|reply_path -%}
                {%- set identifiersItems = repliesMap[identifiersPath]|reply_items -%}
                {%- if identifiersItems|length > 0 -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
