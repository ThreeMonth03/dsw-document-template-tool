# Translation Unit

- Source File: `src/questions/10-share-restrictions.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `no-name-given-not-published-will-be-published-d19a5e386b`
- Unit Key: `we-will-be-adding-a-reference-to-the-db373357ff`
- Source Hash: `bf3d93be7a150a64babe3e51cd982976c086e03d`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We will be adding a reference to the published data to at least one data catalogue.
```

### Source (en)

~~~jinja
We will be adding a reference to the published data to at least one data catalogue.
            {%- endif -%}
            {# When published #}
            {%- set publishedWhenPath = [isPublishedDataPath, uuids.isPublishedDataYesAUuid, uuids.publishedWhenQUuid]|reply_path -%}
            {%- set publishedWhenAUuid = repliesMap[publishedWhenPath]|reply_str_value -%}
            {%- if publishedWhenAUuid == uuids.publishedWhenSoonAUuid %}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
