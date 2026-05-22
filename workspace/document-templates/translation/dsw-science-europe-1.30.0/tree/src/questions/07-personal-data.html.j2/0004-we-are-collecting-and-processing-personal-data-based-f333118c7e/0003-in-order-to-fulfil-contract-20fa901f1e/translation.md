# Translation Unit

- Source File: `src/questions/07-personal-data.html.j2`
- Wrapper Name: `__tr_block_0003`
- Wrapper Order: `4`
- Wrapper Key: `we-are-collecting-and-processing-personal-data-based-f333118c7e`
- Unit Key: `in-order-to-fulfil-contract-20fa901f1e`
- Source Hash: `0d0d0d7409418e82852e60f4e5a6219499183e3a`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
/ in order to fulfil contract.
```

### Source (en)

~~~jinja
{%- elif personalDataLegalBasisReply == uuids.cpersGdprLegalBasisOtherAUuid -%}
                        {%- set personalDataLegalBasisOtherQUuid = [personalDataLegalBasisQUuid, uuids.cpersGdprLegalBasisOtherAUuid, uuids. cpersGdprLegalBasisOtherWhichQUuid ]|reply_path -%}
                        {%- set personalDataLegalBasisOtherReply = repliesMap[personalDataLegalBasisOtherQUuid]|reply_str_value  -%}
                        {%- if personalDataLegalBasisOtherReply == uuids.cpersGdprLegalBasisOtherWhichContractAUui -%}
                            in order to fulfil contract.
~~~

### Translation (zh_Hant)

~~~jinja

~~~
