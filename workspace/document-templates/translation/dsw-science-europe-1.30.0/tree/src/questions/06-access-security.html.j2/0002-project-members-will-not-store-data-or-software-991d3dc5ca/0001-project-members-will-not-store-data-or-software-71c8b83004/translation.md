# Translation Unit

- Source File: `src/questions/06-access-security.html.j2`
- Wrapper Name: `__tr_block_0001`
- Wrapper Order: `2`
- Wrapper Key: `project-members-will-not-store-data-or-software-991d3dc5ca`
- Unit Key: `project-members-will-not-store-data-or-software-71c8b83004`
- Source Hash: `68c8378f55890240e92d3adfc9fe9ac1f1e543c0`
- Edit only the `Translation (zh_Hant)` block below.

### Sentence (en)

```text
Project members will not store data or software on computers in the lab or external hard drives connected to those computers. They / Project members will not carry data with them (e.g. on laptops, USB sticks, or other external media). / They / Project members can carry data with them on encrypted data carriers and password-protected laptops. / They / Project members can carry data with them on encrypted data carriers. / They / Project members can carry data with them on password-protected laptops. All data centers where project data is stored hold appropriate certifications. All project web services are accessible via secure HTTP (https: //.). Project members have been instructed about both generic and specific risks to the project.
```

### Source (en)

~~~jinja
{%- if storeLab %}
          Project members will not store data or software on computers in the lab or external hard drives connected to those computers.{{" "}}
        {%- endif -%}
        {%- if risksCarryHomeAUuid == uuids.risksCarryHomeNoAUuid %}
          {%- if storeLab -%}They{%- else -%}Project members{%- endif %} will not carry data with them (e.g. on laptops, USB sticks, or other external media).
        {%- elif homeEncrypted and homePassword %}
          {%- if storeLab -%}They{%- else -%}Project members{%- endif %} can carry data with them on encrypted data carriers and password-protected laptops.
        {%- elif homeEncrypted %}
          {%- if storeLab -%}They{%- else -%}Project members{%- endif %} can carry data with them on encrypted data carriers.
        {%- elif homePassword %}
          {%- if storeLab -%}They{%- else -%}Project members{%- endif %} can carry data with them on password-protected laptops.
        {%- endif -%}
        {%- if risksCertificationsAUuid == uuids.risksCertificationsYesAUuid %}
          All data centers where project data is stored hold appropriate certifications.
        {%- endif -%}
        {%- if risksHttpsAUuid == uuids.risksHttpsYesAUuid %}
          All project web services are accessible via secure HTTP (https://...).
        {%- endif -%}
        {%- if risksInstructedAUuid == uuids.risksInstructedYesAUuid %}
          Project members have been instructed about both generic and specific risks to the project.
~~~

### Translation (zh_Hant)

~~~jinja

~~~
