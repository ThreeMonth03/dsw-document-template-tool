# Translation Unit

- Source File: `src/questions/11-data-preservation.html.j2`
- Wrapper Name: `__tr_block_0001`
- Wrapper Order: `2`
- Wrapper Key: `we-plan-to-produce-the-following-datasets-no-bcabb3129d`
- Unit Key: `our-national-repository-our-institutional-repository-special-purpose-22b0bf6401`
- Source Hash: `b14f2cd0f29ac8f02c6aee926607245a57ea7c20`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
: {value}. /. / Our national repository. / Our institutional repository. / Special-purpose repository for the project. We will be able to support this repository for a sufficiently long time. The repository will provide download-only service. / The repository will provide a search and simple access interface. / The repository will provide an advanced processing service.
```

### Source (en)

~~~jinja
{%- set generalPurposeRepoNamePath = [distroRepositoryKindPath, uuids.publishedDataRepositoryGeneralPurposeAUuid, uuids.generalPurposeRepoNameQUuid]|reply_path -%}
                    {%- set generalPurposeRepoNameReply = repliesMap[generalPurposeRepoNamePath] -%}
                    {%- if generalPurposeRepoNameReply -%}
                      : {{ macros.integrationFairSharing(generalPurposeRepoNameReply) }}.
                    {%- else -%}.
                    {% endif -%}
                  {%- elif distroRepositoryKindAUuid == uuids.publishedDataRepositoryNationalAUuid %}
                    Our national repository.
                  {%- elif distroRepositoryKindAUuid == uuids.publishedDataRepositoryInstitutionalAUuid %}
                    Our institutional repository.
                  {%- elif distroRepositoryKindAUuid == uuids.publishedDataRepositorySpecialAUuid %}
                    Special-purpose repository for the project.
                    {# Long-term support #}
                    {%- set specialRepoLongTermSupportPath = [distroRepositoryKindPath, uuids.publishedDataRepositorySpecialAUuid, uuids.specialRepoLongTermSupportQUuid]|reply_path -%}
                    {%- set specialRepoLongTermSupportAUuid = repliesMap[specialRepoLongTermSupportPath]|reply_str_value -%}
                    {%- if specialRepoLongTermSupportAUuid == uuids.specialRepoLongTermSupportYesAUuid %}
                      We will be able to support this repository for a sufficiently long time.
                    {%- endif -%}
                    {# Service level #}
                    {%- set specialRepoServiceLevelPath = [distroRepositoryKindPath, uuids.publishedDataRepositorySpecialAUuid, uuids.specialRepoServiceLevelQUuid]|reply_path -%}
                    {%- set specialRepoServiceLevelAUuid = repliesMap[specialRepoServiceLevelPath]|reply_str_value -%}
                    {%- if specialRepoServiceLevelAUuid == uuids.specialRepoServiceLevelDownloadAUuid %}
                      The repository will provide download-only service.
                    {%- elif specialRepoServiceLevelAUuid == uuids.specialRepoServiceLevelSimpleAUuid %}
                      The repository will provide a search and simple access interface.
                    {%- elif specialRepoServiceLevelAUuid == uuids.specialRepoServiceLevelAdvancedAUuid %}
                      The repository will provide an advanced processing service.
                    {%- endif -%}
                  {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
