# Translation Unit

- Source File: `src/questions/10-share-restrictions.html.j2`
- Wrapper Name: `__tr_block_0002`
- Wrapper Order: `3`
- Wrapper Key: `no-name-given-not-published-will-be-published-d19a5e386b`
- Unit Key: `open-shared-with-anyone-shared-with-a-predefined-a27c4465ee`
- Source Hash: `f70e6d21933520c11b4553561010ca41e7741a61`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
Open (shared with anyone) / Shared with a predefined list of people / Closed (not meant for sharing) using a domain-specific repository: {value}. /. We don't need to contact the repository because it is a routine for us. / We have already contacted the repository. / We are going to contact the repository. / We have made other arrangements{value} / using a general-purpose repository: {value}. /. / using our national repository. / using our institutional repository. / using a special-purpose repository for the project.
```

### Source (en)

~~~jinja
<li>
                            {%- if distroShareAUuid == uuids.publishedDistroShareOpenAUuid %}
                                Open (shared with anyone)
                            {%- elif distroShareAUuid == uuids.publishedDistroShareSharedAUuid %}
                                Shared with a predefined list of people
                            {%- elif distroShareAUuid == uuids.publishedDistroShareClosedAUuid %}
                                Closed (not meant for sharing)
                            {%- endif %}
                            {% if distroRepositoryKindAUuid == uuids.publishedDataRepositoryDomainSpecificAUuid %}
                                using a domain-specific repository
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
                                We have made other arrangements{{ ": " ~ domainSpecificRepoContactBeforeOther|dot if domainSpecificRepoContactBeforeOther else "." }}
                                {%- endif -%}
                            {%- elif distroRepositoryKindAUuid == uuids.publishedDataRepositoryGeneralPurposeAUuid %}
                                using a general-purpose repository
                                {%- set generalPurposeRepoNamePath = [distroRepositoryKindPath, uuids.publishedDataRepositoryGeneralPurposeAUuid, uuids.generalPurposeRepoNameQUuid]|reply_path -%}
                                {%- set generalPurposeRepoNameReply = repliesMap[generalPurposeRepoNamePath] -%}
                                {%- if generalPurposeRepoNameReply -%}
                                    : {{ macros.integrationFairSharing(generalPurposeRepoNameReply) }}.
                                {%- else -%}.
                                {%- endif -%}
                            {%- elif distroRepositoryKindAUuid == uuids.publishedDataRepositoryNationalAUuid %}
                                using our national repository.
                            {%- elif distroRepositoryKindAUuid == uuids.publishedDataRepositoryInstitutionalAUuid %}
                                using our institutional repository.
                            {%- elif distroRepositoryKindAUuid == uuids.publishedDataRepositorySpecialAUuid %}
                                using a special-purpose repository for the project.
                            {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
