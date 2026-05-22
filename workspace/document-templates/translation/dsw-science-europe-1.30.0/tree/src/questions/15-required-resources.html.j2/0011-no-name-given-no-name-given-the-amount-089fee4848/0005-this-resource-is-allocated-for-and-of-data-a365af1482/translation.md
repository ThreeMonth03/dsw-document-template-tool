# Translation Unit

- Source File: `src/questions/15-required-resources.html.j2`
- Wrapper Name: `__tr_block_0010`
- Wrapper Order: `11`
- Wrapper Key: `no-name-given-no-name-given-the-amount-089fee4848`
- Unit Key: `this-resource-is-allocated-for-and-of-data-a365af1482`
- Source Hash: `50c3b144cf769a570a7f4d716d933055951d4529`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
This resource is allocated for{value} {value}, and {value} of data. / {value} and {value} of data. / {value} of data.
```

### Source (en)

~~~jinja
<p>
                            This resource is allocated for{{+" "}}
                            {%- if projectCostItemAllocations|length > 2 -%}
                              {{ projectCostItemAllocations[0:-1]|join(", ") }}, and {{ projectCostItemAllocations[-1] }} of data.
                            {%- elif projectCostItemAllocations|length == 2 -%}
                              {{ projectCostItemAllocations[0] }} and {{ projectCostItemAllocations[1] }} of data.
                            {%- else -%}
                              {{ projectCostItemAllocations[0] }} of data.
                            {%- endif %}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
