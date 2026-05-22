# Translation Unit

- Source File: `src/questions/02-what-data.html.j2`
- Wrapper Name: `__tr_block_0008`
- Wrapper Order: `9`
- Wrapper Key: `we-collect-data-from-and-and-the-non-5c00e25839`
- Unit Key: `we-collect-data-from-and-and-the-non-f80437fa3f`
- Source Hash: `eb041c39434efb6cd9cb32a92f74de662aecba37`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
We collect data from {value}. / {value} and {value}. / {value}, {value}, and {value}. The non-equipment datasets are:
```

### Source (en)

~~~jinja
{%- if typesCount > 0 -%}
          We collect data from
          {% if typesCount == 1 -%}
              {{ typesNames[0] }}.
          {%- elif typesCount == 2 -%}
              {{ typesNames[0] }} and {{ typesNames[1] }}.
          {%- else -%}
              {{ typesNames[0] }}, {{ typesNames[1] }}, and {{ typesNames[2] }}.
          {%- endif -%}
        {% endif %}
        {# Datasets #}
        {%- if neqDataSetsItems|length > 0 -%}
          The non-equipment datasets are:
~~~

### Translation (zh_Hant)

~~~jinja

~~~
