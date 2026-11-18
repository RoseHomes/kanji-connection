# Third-party attribution and licensing

Publication audit: 2026-11-18. This page records inspected package metadata and
upstream terms; it does not override the application's All Rights Reserved notice or clear the
private textbook for redistribution.

## Software dependencies

The frontend lock contains 292 dependency entries, including development and
optional platform packages. All declare a license. The local Python inventory
contains 38 distributions with license metadata, classifiers or license files.
This is a license inventory, not a security-vulnerability or ownership certification.

| Dependency group                                                     | Inspected license          |
| -------------------------------------------------------------------- | -------------------------- |
| React/React DOM, React Router, TanStack Query, Supabase JS, Tailwind | MIT                        |
| Lucide React                                                         | ISC                        |
| FastAPI, Pydantic/settings, SQLAlchemy, PyJWT                        | MIT                        |
| Uvicorn, HTTPX                                                       | BSD-3-Clause               |
| Psycopg and psycopg-binary                                           | LGPL-3.0-only              |
| cryptography                                                         | Apache-2.0 OR BSD-3-Clause |

The frontend transitive inventory also includes Apache-2.0, BSD-2-Clause,
BSD-3-Clause, 0BSD, MIT-0, BlueOak-1.0.0, Python-2.0 and MPL-2.0 entries.
Python dependencies include permissive, MPL-2.0, PSF-2.0 and LGPL metadata.
No undeclared/UNLICENSED package was found in the inspected inventories.

The proposed source repository contains manifests/imports, not node_modules,
Python distributions, generated bundles or vendored dependency binaries. Keep
upstream copyright/license notices when redistributing dependency code or built
artifacts. Before a binary/function/bundle release, check the exact installed
license files, including Psycopg's bundled client libraries and applicable
LGPL/MPL obligations. Exclusion from Git does not remove distribution duties
for a future packaged release. This review does not label LGPL as a prohibition
on using the dependency or require the application to adopt an invented license.

Primary references: [Psycopg license](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt),
[binary installation contents](https://www.psycopg.org/psycopg3/docs/basic/install.html).
Package version pins are in the frontend lock and backend requirements; raw
audit inventories remain in ignored local evidence, without public account data.

## Dictionaries and educational references

- **EDRDG JMdict/KANJIDIC2**: credit the Electronic Dictionary Research and
  Development Group and retain the relevant source/license information when
  distributing covered extracts or adaptations. The current publisher statement
  uses CC BY-SA 4.0 and describes attribution/share-alike conditions for the data;
  it does not require the surrounding software to be open source. The private
  snapshots and enriched book records are not part of this source publication.
  See the [EDRDG license statement](https://www.edrdg.org/edrdg/licence.html).
- **Japan Foundation Marugoto**: downloaded teaching resources are not a blanket
  public redistribution grant. Keep the verification spreadsheets and any
  source-derived extracts private unless applicable permission is established.
  See the [copyright policy](https://marugoto.jpf.go.jp/en/copyright/).
- **KanjiPedia**: citation/reference access does not establish a license to
  redistribute its entries. No open content license is assumed from a link.
  See the [publisher site](https://www.kanjipedia.jp/).
- **Original book/PDF**: possession and successful extraction do not establish
  public distribution rights. PDF, JSON, page text, artwork, chapter metadata and
  edition-specific editorial material remain separate from a code license.

The public schema describes structure and contains no source chapter-title
values. Generated root audits and the edition-bound correction layer are now
ignored. The four embedded wording findings were replaced with generic public
sample copy under owner authorization; the repeated scan found no source overlaps.
See the [publication audit](../reports/PUBLICATION_READINESS.md) for scope and evidence.
Exact matches alone are not a conclusion about copying or copyright protection.

## Fonts and illustrations

Noto Sans Japanese and Thai use SIL Open Font License 1.1. The application loads
fonts remotely; no font binary is in the candidate Git set. If self-hosting or
modifying fonts later, preserve the relevant notices and reserved-name conditions.
See the upstream [Japanese font license](https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE)
and [Thai font license](https://github.com/notofonts/thai/blob/main/OFL.txt).
No book artwork or private preview screenshots are included by the publication rules.

## Application source license

The owner has selected **All Rights Reserved**, as recorded in the
[root usage notice](../../README.md#copyright-and-usage). Public source is for
portfolio viewing and evaluation; copying, redistribution, modification and
commercial reuse require prior permission from the copyright holder, subject to
applicable law and GitHub's platform terms. No open-source license was added.
Public GitHub visibility is not equivalent to an open-source license; see
[GitHub's repository licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).
This notice does not claim ownership of external materials, replace their licenses
or grant reuse rights over protected educational material.
