# Science Europe DMP

This is the DMP template recommended by [Science Europe](https://www.scienceeurope.org) in their [Science Europe Guidance Document](https://scienceeurope.org/media/4brkxxe5/se_rdm_practical_guide_extended_final.pdf) designed for use in [Data Stewardship Wizard](https://ds-wizard.org) with [*Common Data Stewardship knowledge model*](https://registry.ds-wizard.org/knowledge-models/dsw:root:latest) and [*Life Sciences DSW Knowledge Model*](https://registry.ds-wizard.org/knowledge-models/dsw:lifesciences:latest). It applies various rules and synthesizes the text answers from questionnaire replies to relevant questions.


## Usage

This template is available through [DSW Registry](https://registry.ds-wizard.org/templates).


## Issues and Contributing

This document template for DSW is available as open-source via GitHub Repository [ds-wizard/science-europe-template](https://github.com/ds-wizard/science-europe-template), you can [report issues](https://github.com/ds-wizard/science-europe-template/issues) there and fork it for customizations or contributions.


### Contributors

* **Marek Suchánek** <[marek.suchanek@ds-wizard.org](mailto:marek.suchanek@ds-wizard.org)>
  * ORCID: [0000-0001-7525-9218](https://orcid.org/0000-0001-7525-9218)
  * GitHub: [@MarekSuchanek](https://github.com/MarekSuchanek)
* **Kryštof Komanec** <[krystof.komanec@ds-wizard.org](mailto:krystof.komanec@ds-wizard.org)>
  * ORCID: [0000-0003-3856-1682](https://orcid.org/0000-0003-3856-1682)
  * GitHub: [@krystofkomanec](https://github.com/krystofkomanec)
* **Rob Hooft** <[rob.hooft@health-ri.nl](mailto:rob.hooft@health-ri.nl)>
  * ORCID: [0000-0001-6825-9439](https://orcid.org/0000-0001-6825-9439)
  * GitHub: [@rwwh](https://github.com/rwwh)
* **Jana Martínková** <[jana.martinkova@ds-wizard.org](mailto:jana.martinkova@ds-wizard.org)>
  * ORCID: [0000-0001-8575-6533](https://orcid.org/0000-0001-8575-6533/)
  * GitHub: [@jmartinkova](https://github.com/jmartinkova)


## Changelog

### 1.30.0

- Adjust to template metamodel version 18.0 (released in DSW 4.29.0)

### 1.29.1

- Adjust to template metamodel version 17.1 (released in DSW 4.26.0)
- Fix affiliation on front page

### 1.29.0

- Fixed rendering risks
- Improved qualified references part
- Updated reused dataset name to use reply string value instead FAIRsharing integration
- Updated dependency on KM to 2.7.0
- Fixed the published dataset to reflect future-oriented statement

### 1.28.0

- Improved affiliation
- Improved text

### 1.27.0

- Updated dependency on KM to 2.6.13
- Fixed legacy integration type

### 1.26.0

- Updated integrations to metamodel version 17.0 (released in DSW 4.22.0)
- Improved minor text flow

### 1.25.0

- Adjusted to template metamodel version 17.0 (released in DSW 4.22.0)
- Fixed typos

### 1.24.0

- Added "General-purpose repository" option to repository type descriptions

### 1.23.0

- Added ORCID Integration
- Added compatible knowledge models to README

### 1.22.0

- Improved Authors of DMP

### 1.21.0

- Adjusted to template metamodel version 16 (released in DSW 4.13.0)

### 1.20.0

- Adjusted to template metamodel version 15 (released in DSW 4.12.0)

### 1.19.1

- Fix issue with `createdBy`

### 1.19.0

- Adjusted to template metamodel version 14 (released in DSW 4.10.0)

### 1.18.1

- Fixed nested bullet points would display unwanted characters

### 1.18.0

- Updated according to the Science Europe DMP template, including the project number, access to private data, and project costs
- Fixed the question regarding data versions to allow for multiple choices
- Corrected the version table and front page

### 1.17.0

- Adjusted to template metamodel version 13 (released in DSW 4.3.0)

### 1.16.1

- Fixed broken images in Word

### 1.16.0

- Adjusted to template metamodel version 12 (released in DSW 4.1.0)

### 1.15.2

- Removed unused code
- Improved wording of storage conventions

### 1.15.1

- Fixed extra `endif`

### 1.15.0

- Updated for `dsw:root:2.5.0`

### 1.14.0

- Switched from `wkhtmltopdf` to `weasyprint` for PDF
- Improved styling for PDF and HTML
- Fixed (non-)reference data in data summary
- Aligned data openness with the KM

### 1.13.0

- Adjusted to template metamodel version 11 (released in DSW 3.20.0)
- Added versions overview / change tracker table

### 1.12.0

- Adjusted to template metamodel version 10 (released in DSW 3.12.0)

### 1.11.0

- Adjusted to template metamodel version 9 (released in DSW 3.10.0)

### 1.10.1

- Fixed Jinja template nesting error

### 1.10.0

- Compatible with `dsw:root:2.4.0`

### 1.9.0

- Adjusted to template metamodel version 8 (released in DSW 3.8.0)

### 1.8.0

- Adjusted to template metamodel version 7 (released in DSW 3.7.0)

### 1.7.0

- Adjusted to template metamodel version 6 (released in DSW 3.6.0)

### 1.6.0

- Adjusted to template metamodel version 5 (released in DSW 3.5.0)

### 1.5.0

- Adjusted to template metamodel version 4 (released in DSW 3.2.0)

### 1.4.1

- Fixed displaying answers related to measured datasets

### 1.4.0

- Adjusted to template metamodel version 3 (released in DSW 2.12.0)

### 1.3.0

- Compatible with `dsw:root:2.3.0`

### 1.2.0

- Adjusted to template metamodel version 2

### 1.1.0

- Compatible with `dsw:root:2.2.0`
- Updated projects and front page as there can be multiple projects specified for a single DMP
- Questions 8, 9, and 10 updated according to DMP Common Standard with dataset - distribution - license hierarchy

### 1.0.0

- Compatible with `dsw:root:2.0.0` and up to `dsw:root:2.1.0`
- Initial version of DMP template created during [ELIXIR BioHackathon Europe 2019](https://www.biohackathon-europe.org)
