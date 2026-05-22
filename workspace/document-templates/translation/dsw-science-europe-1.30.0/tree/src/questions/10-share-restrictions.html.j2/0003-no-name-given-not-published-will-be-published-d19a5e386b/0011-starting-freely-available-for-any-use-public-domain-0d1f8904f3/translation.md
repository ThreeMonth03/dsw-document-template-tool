# Translation Unit

- Source File: `src/questions/10-share-restrictions.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `no-name-given-not-published-will-be-published-d19a5e386b`
- Unit Key: `starting-freely-available-for-any-use-public-domain-0d1f8904f3`
- Source Hash: `7450135b1486fde23d1db5f1407731b870236296`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
Starting {licenseStart}: Freely available for any use (public domain or CC0). / Freely available with obligation to quote the source (e.g. CC-BY). / Available under some restrictions, which we will follow in our project{value} Re-users will be able to get access by request to the contact person. / Re-users will be able to get access through a
```

### Source (en)

~~~jinja
{%- set licensePrefix = [licensesPath, k]|reply_path -%}
                                {%- set licenseStartPath = [licensePrefix, uuids.publishedDataLicenseStartQUuid]|reply_path -%}
                                {%- set licenseStart = repliesMap[licenseStartPath]|reply_str_value -%}
                                {% if licenseStart %}
                                    Starting {{ licenseStart }}: 
                                {% endif %}
                                
                                {%- set publishedDataLicensePath = [licensePrefix, uuids.publishedDataLicenseQUuid]|reply_path -%}
                                {%- set publishedDataLicenseAUuid = repliesMap[publishedDataLicensePath]|reply_str_value -%}
                                {%- if publishedDataLicenseAUuid == uuids.publishedDataLicenseCC0AUuid %}
                                    Freely available for any use (public domain or CC0).
                                {%- elif publishedDataLicenseAUuid == uuids.publishedDataLicenseCCBYAUuid %}
                                    Freely available with obligation to quote the source (e.g. CC-BY).
                                {%- elif publishedDataLicenseAUuid == uuids.publishedDataLicenseRestrictAUuid -%}
                                    {%- set licenseRestrictConditionsPath = [publishedDataLicensePath, uuids.publishedDataLicenseRestrictAUuid, uuids.licenseRestrictConditionsQUuid]|reply_path -%}
                                    {%- set licenseRestrictConditions = repliesMap[licenseRestrictConditionsPath]|reply_str_value -%}
                                    {%- set licenseRestrictLinkPath = [publishedDataLicensePath, uuids.publishedDataLicenseRestrictAUuid, uuids.licenseRestrictLinkQUuid]|reply_path -%}
                                    {%- set licenseRestrictLink = repliesMap[licenseRestrictLinkPath]|reply_str_value -%}
                                    {%- set licenseRestrictAccessPath = [publishedDataLicensePath, uuids.publishedDataLicenseRestrictAUuid, uuids.licenseRestrictAccessQUuid]|reply_path -%}
                                    {%- set licenseRestrictAccessAUuid = repliesMap[licenseRestrictAccessPath]|reply_str_value -%}
                                    {%- set licenseRestrictMetadataPath = [publishedDataLicensePath, uuids.publishedDataLicenseRestrictAUuid, uuids.licenseRestrictMetadataQUuid]|reply_path -%}
                                    {%- set licenseRestrictMetadataAUuid = repliesMap[licenseRestrictMetadataPath]|reply_str_value %}
                                    
                                    Available under some restrictions, which we will follow in our project{{ ": " ~ licenseRestrictConditions|dot if licenseRestrictConditions else "." }}
                                    {%- if licenseRestrictAccessAUuid == uuids.licenseRestrictAccessRequestAUuid %}
                                    Re-users will be able to get access by request to the contact person.
                                    {%- elif licenseRestrictAccessAUuid == uuids.licenseRestrictAccessCommitteeAUuid %}
                                    Re-users will be able to get access through a
~~~

### Translation (zh_Hant)

~~~jinja

~~~
