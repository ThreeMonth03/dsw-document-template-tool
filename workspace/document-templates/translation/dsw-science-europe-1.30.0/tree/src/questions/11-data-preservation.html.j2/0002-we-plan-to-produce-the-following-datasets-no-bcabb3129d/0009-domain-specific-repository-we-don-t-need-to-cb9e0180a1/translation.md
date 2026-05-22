# Translation Unit

- Source File: `src/questions/11-data-preservation.html.j2`
- Wrapper Name: `__tr_block_0001`
- Wrapper Order: `2`
- Wrapper Key: `we-plan-to-produce-the-following-datasets-no-bcabb3129d`
- Unit Key: `domain-specific-repository-we-don-t-need-to-cb9e0180a1`
- Source Hash: `82d370e907ea0b08f6c4152bde6beae9ca82ddf9`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
Domain-specific repository: {value}. /. We don't need to contact the repository because it is a routine for us. / We have already contacted the repository. / We are going to contact the repository. / We have made other arrangements instead of contacting the repository directly{value} /
```

### Source (en)

~~~jinja
{%- if distroRepositoryKindAUuid == uuids.publishedDataRepositoryDomainSpecificAUuid %}
                    Domain-specific repository
                    {%- set domainSpecificRepoNamePath = [distroRepositoryKindPath, uuids.publishedDataRepositoryDomainSpecificAUuid, uuids.domainSpecificRepoNameQUuid]|reply_path -%}
                    {%- set domainSpecificRepoNameReply = repliesMap[domainSpecificRepoNamePath] -%}
                    {%- if domainSpecificRepoNameReply -%}
                      : {{ macros.integrationFairSharing(domainSpecificRepoNameReply) }}.
                    {%- else -%}.
                    {% endif -%}
                    {# Contact the repository #}
                    {%- set domainSpecificRepoContactBeforePath = [distroRepositoryKindPath, uuids.publishedDataRepositoryDomainSpecificAUuid, uuids.domainSpecificRepoContactBeforeQUuid]|reply_path -%}
                    {%- set domainSpecificRepoContactBeforeAUuid = repliesMap[domainSpecificRepoContactBeforePath]|reply_str_value -%}
                    {%- if domainSpecificRepoContactBeforeAUuid == uuids.domainSpecificRepoContactBeforeNoAUuid %}
                      We don't need to contact the repository because it is a routine for us.
                    {%- elif domainSpecificRepoContactBeforeAUuid == uuids.domainSpecificRepoContactBeforeYesAlreadyAUuid %}
                      We have already contacted the repository.
                    {%- elif domainSpecificRepoContactBeforeAUuid == uuids.domainSpecificRepoContactBeforeYesWillAUuid %}
                      We are going to contact the repository.
                    {%- elif domainSpecificRepoContactBeforeAUuid == uuids.domainSpecificRepoContactBeforeOtherAUuid %}
                      {%- set domainSpecificRepoContactBeforeOtherPath = [domainSpecificRepoContactBeforePath, uuids.domainSpecificRepoContactBeforeOtherAUuid, uuids.domainSpecificRepoContactBeforeOtherQUuid]|reply_path -%}
                      {%- set domainSpecificRepoContactBeforeOther = repliesMap[domainSpecificRepoContactBeforeOtherPath]|reply_str_value %}
                      We have made other arrangements instead of contacting the repository directly{{ ": " ~ domainSpecificRepoContactBeforeOther|dot if domainSpecificRepoContactBeforeOther else "." }}
                    {%- endif -%}
                  {%- elif distroRepositoryKindAUuid == uuids.publishedDataRepositoryGeneralPurposeAUuid %}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
