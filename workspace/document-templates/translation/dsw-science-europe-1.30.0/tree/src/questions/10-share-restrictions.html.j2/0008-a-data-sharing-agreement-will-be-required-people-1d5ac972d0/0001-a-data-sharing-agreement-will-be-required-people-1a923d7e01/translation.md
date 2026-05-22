# Translation Unit

- Source File: `src/questions/10-share-restrictions.html.j2`
- Wrapper Name: `__tr_block_0007`
- Wrapper Order: `8`
- Wrapper Key: `a-data-sharing-agreement-will-be-required-people-1d5ac972d0`
- Unit Key: `a-data-sharing-agreement-will-be-required-people-1a923d7e01`
- Source Hash: `b2e55b1c9022c96e97b18a6a1da47c7b54c7c7ac`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
A data sharing agreement will be required. People can apply to one of the project members. / People can apply to the data access committee that we will set up. / People can apply to the
```

### Source (en)

~~~jinja
A data sharing agreement will be required.
          {%- set legalReasonsAuthorizePath = [legalReasonsAuthenticatedPath, uuids.legalReasonsAuthenticatedYesAUuid, uuids.legalReasonsAuthorizeQUuid]|reply_path -%}
          {%- set legalReasonsAuthorizeAUuid = repliesMap[legalReasonsAuthorizePath]|reply_str_value -%}
          {%- if legalReasonsAuthorizeAUuid == uuids.legalReasonsAuthorizeMemberAUuid %}
            People can apply to one of the project members.
          {%- elif legalReasonsAuthorizeAUuid == uuids.legalReasonsAuthorizeNewCommitteeAUuid %}
            People can apply to the data access committee that we will set up.
          {%- elif legalReasonsAuthorizeAUuid == uuids.legalReasonsAuthorizeOldCommitteeAUuid %}
            {%- set legalReasonsAuthorizeOldCommitteePath = [legalReasonsAuthorizePath, uuids.legalReasonsAuthorizeOldCommitteeAUuid, uuids.legalReasonsAuthorizeOldCommitteeQUuid]|reply_path -%}
            {%- set legalReasonsAuthorizeOldCommittee = repliesMap[legalReasonsAuthorizeOldCommitteePath]|reply_str_value -%}
            {%- if legalReasonsAuthorizeOldCommittee %}
              People can apply to the
~~~

### Translation (zh_Hant)

~~~jinja

~~~
