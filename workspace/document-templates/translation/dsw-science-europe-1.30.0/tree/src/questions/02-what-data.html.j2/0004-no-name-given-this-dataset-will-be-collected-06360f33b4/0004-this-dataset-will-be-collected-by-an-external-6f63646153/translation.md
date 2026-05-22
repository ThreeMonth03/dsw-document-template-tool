# Translation Unit

- Source File: `src/questions/02-what-data.html.j2`
- Wrapper Name: `__tr_block_0003`
- Wrapper Order: `4`
- Wrapper Key: `no-name-given-this-dataset-will-be-collected-06360f33b4`
- Unit Key: `this-dataset-will-be-collected-by-an-external-6f63646153`
- Source Hash: `0f6778437522c098f7ed87ce6e9daaffd4beda26`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
This dataset will be collected by an external party. The ownership of the resulting data will remain with the external party. / The project partners acquire full ownership of the data. / For the ownership of the data we have made the following arrangements: {mdExternalOwnershipOther}
```

### Source (en)

~~~jinja
<p>
                This dataset will be collected by an external party.
                {% if mdExternalOwnershipAUuid == uuids.mdExternalOwnershipPartyAUuid -%}
                  The ownership of the resulting data will remain with the external party.
                {%- elif mdExternalOwnershipAUuid == uuids.mdExternalOwnershipPartnersAUuid -%}
                  The project partners acquire full ownership of the data.
                {%- elif mdExternalOwnershipAUuid == uuids.mdExternalOwnershipOtherAUuid -%}
                  {%- set mdExternalOwnershipOtherPath = [mdExternalOwnershipPath, uuids.mdExternalOwnershipOtherAUuid, uuids.mdExternalOwnershipOtherQUuid]|reply_path -%}
                  {%- set mdExternalOwnershipOther = repliesMap[mdExternalOwnershipOtherPath]|reply_str_value -%}
                  {%- if mdExternalOwnershipOther -%}
                    For the ownership of the data we have made the following arrangements: {{ mdExternalOwnershipOther|dot }}
                  {%- endif -%}
                {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
