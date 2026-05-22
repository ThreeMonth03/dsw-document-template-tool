# Translation Unit

- Source File: `src/questions/10-share-restrictions.html.j2`
- Wrapper Name: `__tr_block_0007`
- Wrapper Order: `8`
- Wrapper Key: `a-data-sharing-agreement-will-be-required-people-1d5ac972d0`
- Unit Key: `data-access-committee-people-can-apply-to-an-303405d757`
- Source Hash: `809f33385f046e3c4996f1712abd68ede486b7cd`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
data access committee. / People can apply to an existing data access committee. / For the authorization of potential users, we will make special arrangements{value}
```

### Source (en)

~~~jinja
data access committee.
            {%- else -%}
              People can apply to an existing data access committee.
            {%- endif -%}
          {%- elif legalReasonsAuthorizeAUuid == uuids.legalReasonsAuthorizeOtherAUuid %}
            {%- set legalReasonsAuthorizeOtherPath = [legalReasonsAuthorizePath, uuids.legalReasonsAuthorizeOtherAUuid, uuids.legalReasonsAuthorizeOtherQUuid]|reply_path -%}
            {%- set legalReasonsAuthorizeOther = repliesMap[legalReasonsAuthorizeOtherPath]|reply_str_value %}
            For the authorization of potential users, we will make special arrangements{{ ": " ~ legalReasonsAuthorizeOther|dot if legalReasonsAuthorizeOther else "." }}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
