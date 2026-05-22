# Translation Unit

- Source File: `src/questions/15-required-resources.html.j2`
- Wrapper Name: `__tr_block_0010`
- Wrapper Order: `11`
- Wrapper Key: `no-name-given-no-name-given-the-amount-089fee4848`
- Unit Key: `ensuring-findability-ensuring-accessibility-ensuring-interoperability-ensuring-reusability-c6a3c82f9b`
- Source Hash: `90f001580c97c64a528aebce98ddfc5e562601fc`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
ensuring findability ensuring accessibility ensuring interoperability ensuring reusability supporting management
```

### Source (en)

~~~jinja
{%- endif -%}

                        {%- set projectCostItemAllocationQUuid = [projectCostItem, uuids.costAllocationQUuid]|reply_path  -%}
                        {%- set projectCostItemAllocationItems = repliesMap[projectCostItemAllocationQUuid]|reply_items -%}

                        
                          {%- set projectCostItemAllocations = [] -%}
                          {%- if uuids.costAllocationFindabilityAUuid in projectCostItemAllocationItems -%}
                            {%- do projectCostItemAllocations.append("ensuring findability") -%}
                          {%- endif -%}
                          {%- if uuids.costAllocationAccessibilityAUuid in projectCostItemAllocationItems -%}
                            {%- do projectCostItemAllocations.append("ensuring accessibility") -%}
                          {%- endif -%}
                          {%- if uuids.costAllocationInteroperabilityAUuid in projectCostItemAllocationItems -%}
                            {%- do projectCostItemAllocations.append("ensuring interoperability") -%}
                          {%- endif -%}
                          {%- if uuids.costAllocationReusabilityAUuid in projectCostItemAllocationItems -%}
                            {%- do projectCostItemAllocations.append("ensuring reusability") -%}
                          {%- endif -%}
                          {%- if uuids.costManagementAUuid in projectCostItemAllocationItems -%}
                            {%- do projectCostItemAllocations.append("supporting management") -%}
                          {%- endif -%}
                        
                        {%- if projectCostItemAllocations|length > 0 -%}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
