# Translation Unit

- Source File: `src/questions/15-required-resources.html.j2`
- Wrapper Name: `__tr_block_0010`
- Wrapper Order: `11`
- Wrapper Key: `no-name-given-no-name-given-the-amount-089fee4848`
- Unit Key: `this-cost-will-be-covered-by-funding-grant-2aed585f84`
- Source Hash: `42e631d22b2eb37525e9d01ff18399e665b0dd19`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
This cost will be covered by funding grant (grant number: {costCoverGrantIdReply}) /.
```

### Source (en)

~~~jinja
<p>This cost will be covered by funding grant
                          {%- if costCoverGrantIdReply -%}
                            {{" "}}(grant number: {{costCoverGrantIdReply}})
                          {%- else -%}
                            . </p>
                          {%- endif -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
