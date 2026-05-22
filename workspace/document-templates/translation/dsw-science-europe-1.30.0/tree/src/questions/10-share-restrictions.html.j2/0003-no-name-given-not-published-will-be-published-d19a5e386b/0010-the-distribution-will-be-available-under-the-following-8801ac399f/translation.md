# Translation Unit

- Source File: `src/questions/10-share-restrictions.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `no-name-given-not-published-will-be-published-d19a5e386b`
- Unit Key: `the-distribution-will-be-available-under-the-following-8801ac399f`
- Source Hash: `19ca05a98e6bcaf2e2686395ad6cd3c3288c896f`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
The distribution will be available under the following licenses / license:
```

### Source (en)

~~~jinja
{%- endif -%}
                        {# Licenses #}
                        {%- set licensesPath = [distroPrefix, uuids.publishedDataLicensesQUuid]|reply_path -%}
                        {%- set licensesItems = repliesMap[licensesPath]|reply_items -%}
                        {%- if licensesItems|length > 0 %}
                            The distribution will be available under the following {{ "licenses" if licensesItems|length > 1 else "license" }}:
~~~

### Translation (zh_Hant)

~~~jinja

~~~
