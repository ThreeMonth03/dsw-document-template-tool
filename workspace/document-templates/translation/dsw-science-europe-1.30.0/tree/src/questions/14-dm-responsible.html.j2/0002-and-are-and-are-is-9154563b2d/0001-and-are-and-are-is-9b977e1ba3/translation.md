# Translation Unit

- Source File: `src/questions/14-dm-responsible.html.j2`
- Wrapper Name: `__tr_block_0001`
- Wrapper Order: `2`
- Wrapper Key: `and-are-and-are-is-9154563b2d`
- Unit Key: `and-are-and-are-is-9b977e1ba3`
- Source Hash: `e510a509848095ec8dabc98022d405b1e6cc8e6a`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
{value}, and {value} are {responsibility} / {value} and {value} are {responsibility} / {value} is {responsibility}
```

### Source (en)

~~~jinja
{%- if nNames > 2 -%}
              {{ names[0:-1]|join(", ") }}, and {{ names[-1] }} are {{ responsibility }}
            {%- elif nNames == 2 -%}
              {{ names[0] }} and {{ names[1] }} are {{ responsibility }}
            {%- else -%}
              {{ names[0] }} is {{ responsibility }}
~~~

### Translation (zh_Hant)

~~~jinja

~~~
