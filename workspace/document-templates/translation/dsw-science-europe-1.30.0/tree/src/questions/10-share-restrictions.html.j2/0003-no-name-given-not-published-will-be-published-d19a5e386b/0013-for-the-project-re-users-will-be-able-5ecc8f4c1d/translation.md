# Translation Unit

- Source File: `src/questions/10-share-restrictions.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `no-name-given-not-published-will-be-published-d19a5e386b`
- Unit Key: `for-the-project-re-users-will-be-able-5ecc8f4c1d`
- Source Hash: `a0d43a726d3e57e056b8a725f877118442a0ad5d`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
for the project. / Re-users will be able to get access through a specialized process{value} The conditions will be published as part of open metadata. More information about the restrictions can be found here:
```

### Source (en)

~~~jinja
for the project.
                                    {%- elif licenseRestrictAccessAUuid == uuids.licenseRestrictAccessAnotherAUuid -%}
                                    {%- set licenseRestrictAccessAnotherPath = [licenseRestrictAccessPath, uuids.licenseRestrictAccessAnotherAUuid, uuids.licenseRestrictAccessAnotherQUuid]|reply_path -%}
                                    {%- set licenseRestrictAccessAnother = repliesMap[licenseRestrictAccessAnotherPath]|reply_str_value %}
                                    Re-users will be able to get access through a specialized process{{ ": " ~ licenseRestrictAccessAnother|dot if licenseRestrictAccessAnother else "." }}
                                    {%- endif -%}
                                    {%- if licenseRestrictMetadataAUuid == uuids.licenseRestrictMetadataYesAUuid %}
                                    The conditions will be published as part of open metadata.
                                    {%- endif -%}
                                    {% if licenseRestrictLink %}
                                    More information about the restrictions can be found here:
~~~

### Translation (zh_Hant)

~~~jinja

~~~
