# Translation Unit

- Source File: `src/questions/01-how-data.html.j2`
- Wrapper Name: `__tr_block_0006`
- Wrapper Order: `7`
- Wrapper Key: `no-name-given-we-will-re-use-this-6759c9c657`
- Unit Key: `this-data-include-personal-data-legaly-based-on-b880bb4071`
- Source Hash: `204dd90f83ad79b00513d9abf932ff552fb0f509`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
This data include personal data, legaly based on{value} public interest for processing the data under GDPR. / consent given by the research subject for processing the data under GDPR, which{value} covers also our reuse. / does not cover our reuse; therefore, new consent will be needed. /. / a legal requirement (meaning a legal obligation to do this data processing). / a vital interest (meaning it needs to be done to protect the vital interests of the data subject). / a legitimate interest (meaning data subjects all expect us to do this data processing because of who we are). / a requirement to fulfill our contract with the data subjects.
```

### Source (en)

~~~jinja
<p>
            This data include personal data
            {%- set nrefDataPersonalLegalBasis = [nrefDataPersonal, uuids.nrefDataPersonalYesAUuid, uuids.nrefDataPersonalLegalBasisQUuid]|reply_path -%}
            {%- set nrefDataPersonalLegalBasisReply = repliesMap[nrefDataPersonalLegalBasis]|reply_str_value -%}
            {%- if nrefDataPersonalLegalBasisReply -%}
              , legaly based on{{+" "}}
              {%- if nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisPubInterestAUuid -%}
                public interest for processing the data under GDPR.
              {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLegalBasisConsentAUuid -%}
                consent given by the research subject for processing the data under GDPR
                {%- set nrefDataPersonalLegalBasisReuse = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLegalBasisConsentAUuid, uuids.nrefDataPersonalLegalBasisConsentReuseQUuid]|reply_path -%}
                {%- set nrefDataPersonalLegalBasisReuseReply = repliesMap[nrefDataPersonalLegalBasisReuse]|reply_str_value -%}
                {%- if nrefDataPersonalLegalBasisReuseReply -%}
                  , which{{+" "}}
                  {%- if nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseYesAUuid -%}
                    covers also our reuse.
                  {%- elif nrefDataPersonalLegalBasisReuseReply == uuids.nrefDataPersonalLegalBasisConsentReuseNoAUuid -%}
                    does not cover our reuse; therefore, new consent will be needed.
                  {%- endif -%}
                {%- else -%}
                .
                {%- endif -%}
              {%- elif nrefDataPersonalLegalBasisReply == uuids.nrefDataPersonalLebalBasisOtherAUuid -%}
                {%- set nrefDataPersonalLegalBasisOther = [nrefDataPersonalLegalBasis, uuids.nrefDataPersonalLebalBasisOtherAUuid, uuids.nrefDataPersonalLegalBasisOtherQUuid]|reply_path -%}
                {%- set nrefDataPersonalLegalBasisOtherReply = repliesMap[nrefDataPersonalLegalBasisOther]|reply_str_value -%}
                {%- if nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegalAUuid -%}
                  a legal requirement (meaning a legal obligation to do this data processing).
                {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherVitalAUuid -%}
                  a vital interest (meaning it needs to be done to protect the vital interests of the data subject).
                {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherLegitAUuid -%}
                  a legitimate interest (meaning data subjects all expect us to do this data processing because of who we are).
                {%- elif nrefDataPersonalLegalBasisOtherReply == uuids.nrefDataPersonalLegalBasisOtherContractAUuid -%}
                  a requirement to fulfill our contract with the data subjects.
                {%- endif -%}
              {%- endif -%} 
            {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
