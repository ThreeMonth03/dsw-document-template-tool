# Translation Unit

- Source File: `src/questions/10-share-restrictions.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `no-name-given-not-published-will-be-published-d19a5e386b`
- Unit Key: `the-dataset-will-published-after-an-embargo-44c3097704`
- Source Hash: `703ea1e23fc21868157fc43d76e77a46086806a8`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
The dataset will published after an embargo.
```

### Source (en)

~~~jinja
The dataset will published after an embargo.
            {%- endif %}
            {# Qualified references #}
            {%- set publishedQReferencesPath = [isPublishedDataPath, uuids.isPublishedDataYesAUuid, uuids.publishedQReferencesQUuid]|reply_path -%}
            {%- set publishedQReferencesAUuid = repliesMap[publishedQReferencesPath]|reply_str_value -%}
            {%- if publishedQReferencesAUuid == uuids.publishedQReferencesYesAUuid -%}
                {%- set publishedQReferencesItemsPath = [publishedQReferencesPath, uuids.publishedQReferencesYesAUuid, uuids.publishedQReferencesItemQUuid ]|reply_path -%}
                {%- set publishedQReferencesItems = repliesMap[publishedQReferencesItemsPath]|reply_items -%}
                {%- set qreferences = [] -%}
                {%- for item in publishedQReferencesItems -%}
                    {%- set refId = repliesMap[[publishedQReferencesItemsPath, item, uuids.publishedQReferenceIdQUuid]|reply_path]|reply_str_value|e -%}
                    {%- set refRel = repliesMap[[publishedQReferencesItemsPath, item, uuids.publishedQReferenceRelQUuid]|reply_path]|reply_str_value|e -%}
                    {%- if refId and refRel -%}
                    {%- do qreferences.append({
                        'id': refId,
                        'relation': refRel,
                    }) -%}
                    {%- endif -%}
                {%- endfor -%}
            {%- endif -%}
            {%- if qreferences|length > 0 -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
