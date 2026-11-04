"""Source-qualified PIRR programme references and publication crosswalks.

PIRR identifies research programmes. DOI and local archive references identify
different entities and must never be promoted to invented PIRR work identifiers.
"""
from copy import deepcopy
import csv
from html import escape
from io import StringIO
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


def _e(value):
    return escape(str(value or ""), quote=True)


def load_pirr(path=None):
    return json.loads(Path(path or Path(__file__).resolve().parents[1] / "data/pirr.json").read_text())


def _url(value):
    parsed = urlsplit(value)
    return parsed.scheme + "://" + parsed.netloc + parsed.path.rstrip("/") + "/"


def _validate(data):
    keys, identifiers = set(), set()
    patterns = {"PIRR programme reference": r"moo-program-[a-z0-9]+", "PIRR project ID": r"pir-prj-[a-z0-9]+"}
    for programme in data["programmes"]:
        key = programme["key"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key) or key in keys:
            raise ValueError("Invalid or duplicate PIRR crosswalk programme key: " + key)
        keys.add(key)
        if not programme.get("source_url", "").startswith("https://www.museumofone.art/"):
            raise ValueError("Programme crosswalk requires a public source account")
        for identifier in programme.get("identifiers", []):
            pattern = patterns.get(identifier["scheme"])
            if not pattern or not re.fullmatch(pattern, identifier["value"]):
                raise ValueError("Identifier namespace does not match its published label")
            if identifier["value"] in identifiers or not identifier.get("source_url"):
                raise ValueError("Duplicate or unsourced PIRR identifier")
            identifiers.add(identifier["value"])
    for relation in data.get("programme_relations", []):
        if relation["from"] not in keys or relation["to"] not in keys or not relation.get("source_url"):
            raise ValueError("Unresolved or unsourced programme relationship")


def attach_pirr(records, programmes, data):
    """Return independent record/programme copies with evidence-scoped links.

    A publication's existing work-specific research-programme badge is the
    relationship evidence. No relationship is inferred from the global site nav.
    Publication component links are navigational access through their parent;
    programme attribution is not independently assigned to individual chapters.
    """
    _validate(data)
    records, programmes = deepcopy(records), deepcopy(programmes)
    by_url = {_url(p["url"]): p for p in data["programmes"]}
    for programme in programmes:
        for field in ("pirr_record", "pirr_registry_url", "pirr_reference", "pirr_project_id"):
            programme.pop(field, None)
        context = by_url.get(_url(programme["url"]))
        if context:
            programme["pirr_record"] = deepcopy(context)
            programme["pirr_registry_url"] = "research-registry.html#" + context["key"]
            for identifier in context.get("identifiers", []):
                field = "pirr_reference" if identifier["scheme"] == "PIRR programme reference" else "pirr_project_id"
                programme[field] = identifier["value"]
    for record in records:
        record["pirr_references"] = []
        for link in record.get("research_programmes", []):
            context = by_url.get(_url(link["url"]))
            if not context:
                continue
            record["pirr_references"].append({
                "programme_key": context["key"], "programme_title": context["title"],
                "programme_url": context["url"], "programme_stage": context["stage"],
                "registry_url": "research-registry.html#" + context["key"],
                "identifiers": deepcopy(context.get("identifiers", [])),
                "relation": link.get("relation_label") or link.get("relation") or "Related public programme account",
                "relation_note": link.get("relation", ""),
                "source_url": link.get("source_url") or record.get("institutional_url") or context["url"],
            })
        record["pirr_work_identity"] = {
            "archive_reference": record.get("accession", ""),
            "edition_doi": str(record.get("doi") or "").removeprefix("https://doi.org/"),
            "zenodo_record_id": str(record["id"]),
            "identifier_scope": "Publication identity; PIRR identifiers in programme relationships identify research records, not this publication.",
        }
    return records, programmes


def pirr_item_panel(record, base="../"):
    """Reciprocal research access from an item, retaining relationship evidence."""
    links = record.get("pirr_references", [])
    if not links:
        return ""
    body = '<section class="item-section pirr-context" id="pirr-context"><div class="section-no">PIRR / Research record crosswalk</div><h2>Research programme connections</h2><p>Follow this publication into its research context and explore related work. Programme stage and publication status are described separately.</p><dl class="metadata">'
    for link in links:
        ids = " · ".join(f'{_e(i["scheme"])}: <code>{_e(i["value"])}</code>' for i in link["identifiers"])
        body += (f'<div><dt><a href="{_e(base + link["registry_url"])}">{_e(link["programme_title"])}</a></dt>'
                 f'<dd>{_e(link["relation"])}<small>{_e(link["relation_note"])}</small>'
                 f'<p>{ids or "No public PIRR identifier transcribed for this programme account."}</p>'
                 f'<a href="{_e(link["programme_url"])}">Public programme record ↗</a> · '
                 f'<a href="{_e(link["source_url"])}">Work–programme relationship source ↗</a></dd></div>')
    return body + '</dl><p><a href="' + _e(base) + 'research-registry.html">Search all research references and related publications ↗</a></p></section>'


def _publication(record, link=None):
    doi = str(record.get("doi") or "").removeprefix("https://doi.org/")
    body = (f'<li><div class="catalogue-id">{_e(record.get("accession"))} · Published item</div>'
            f'<h4><a href="items/{_e(record["id"])}.html">{_e(record["title"])}</a></h4>'
            f'<p><a href="https://doi.org/{_e(doi)}">DOI: {_e(doi)}</a> · '
            f'<a href="read/{_e(record["id"])}.html">Read publication ↗</a></p>')
    if link:
        body += f'<p>{_e(link["relation"])} <a href="{_e(link["source_url"])}">Relationship evidence ↗</a></p>'
        if link.get("relation_note") and link["relation_note"] != link["relation"]:
            body += f'<p class="registry-relation-note">{_e(link["relation_note"])}</p>'
    if record.get("contents"):
        body += '<details class="registry-components"><summary>Explore ' + str(len(record["contents"])) + ' chapters and supporting texts</summary><p>Component access follows the parent publication; these local analytic descriptions carry no separate PIRR programme attribution or DOI.</p><ul>'
        for part in record["contents"]:
            body += f'<li><a href="{_e(part["url"])}">{_e(part["reference"])} · {_e(part["title"])}</a> · <a href="{_e(part["reader_url"])}">Read from page {_e(part["pdf_start"])} ↗</a></li>'
        body += '</ul></details>'
    return body + '</li>'


def build_pirr_pages(records, programmes, data, write, layout, origin):
    """Write searchable programme/publication crosswalk and reusable exports."""
    records, programmes = attach_pirr(records, programmes, data)
    by_key = {p["key"]: p for p in data["programmes"]}
    linked = sum(bool(r["pirr_references"]) for r in records)
    identifiers = sum(len(p.get("identifiers", [])) for p in data["programmes"])
    body = ('<div class="page-head"><div class="breadcrumb"><a href="index.html">Archive</a> / Research registry</div>'
            '<div class="eyebrow">Post-Interpretive Research Registry / Public research crosswalk</div>'
            '<h1>Follow the research</h1><p>Move between research questions, published programme references, deposited editions and the texts within them.</p>'
            f'<div class="action-row"><a class="button" href="{_e(data["registry_url"])}">Museum of One research registry ↗</a>'
            '<a class="text-link" href="programmes.html">Research pathways ↗</a><a class="text-link" href="data/research-crosswalk.json" download>JSON crosswalk ↓</a><a class="text-link" href="data/research-crosswalk.csv" download>CSV references ↓</a></div></div>'
            f'<section class="item-section"><div class="section-no">{len(by_key):02d} programme accounts · {identifiers:02d} published research identifiers · {linked:02d} linked archive items</div>'
            '<h2>Search the research record</h2><form role="search" action="research-registry.html" method="get" id="registry-search-form"><label for="registry-search">Programme, research question, PIRR ID, DOI, item number or text title</label><div class="action-row"><input type="search" name="q" id="registry-search" placeholder="Try: pir-prj-pyp5yx3w or historical answerability" autocomplete="off"><button class="button" type="submit">Find references</button><button type="button" class="button button-outline" id="registry-reset">Show all</button></div></form><p id="registry-results" role="status" aria-live="polite"></p></section>'
            '<section class="item-section"><h2>Reading the identifiers</h2><dl class="metadata"><div><dt>PIRR project ID</dt><dd>Identifies a registered programme record in Museum of One’s research infrastructure.</dd></div><div><dt>PIRR programme reference</dt><dd>Connects a working research record with its public programme account.</dd></div><div><dt>Publication DOI / Zenodo record</dt><dd>Identifies a deposited publication edition. Its identity is retained when linked to a programme.</dd></div><div><dt>Archive / component reference</dt><dd>Identifies a local catalogue description. A component reference leads to a text inside its parent edition.</dd></div></dl>'
            f'<p><a href="{_e(data.get("registry_source_url", data["registry_url"]))}">Source: Museum of One’s explanation of PIRR and reference types ↗</a>. Source review: {_e(data["reviewed"])}.</p></section><div class="registry-directory">')
    export = {"reviewed": data["reviewed"], "scope": data["scope"], "archive_origin": origin.rstrip("/"), "registry_url": data["registry_url"], "programmes": deepcopy(data["programmes"]), "programme_relations": deepcopy(data.get("programme_relations", [])), "publications": []}
    for p in data["programmes"]:
        related = [(r, link) for r in records for link in r["pirr_references"] if link["programme_key"] == p["key"]]
        search = " ".join([p["title"], p.get("question", ""), p.get("responsibility", ""), p.get("form", ""), p.get("current_work", "")] + [i["value"] for i in p.get("identifiers", [])] + [source["title"] for source in p.get("public_sources", [])] + [str(v) for r, _ in related for v in [r["title"], r.get("accession"), r.get("doi")]] + [str(part.get(field) or "") for r, _ in related for part in r.get("contents", []) for field in ("title", "reference")])
        body += (f'<article class="item-section registry-record" id="{_e(p["key"])}" data-registry-entry data-search="{_e(search)}">'
                 f'<div class="section-no">Programme account · {_e(p["stage"])}</div><h2>{_e(p["title"])}</h2>'
                 f'<p class="registry-question">{_e(p.get("question", "Follow the public programme account for the current research question and scope."))}</p><dl class="metadata">')
        for field, label in [("responsibility", "Responsibility in programme source"), ("form", "Research form")]:
            if p.get(field):
                body += f'<div><dt>{label}</dt><dd>{_e(p[field])}</dd></div>'
        for identifier in p.get("identifiers", []):
            body += f'<div id="{_e(identifier["value"])}"><dt>{_e(identifier["scheme"])}</dt><dd><code>{_e(identifier["value"])}</code> · <a href="{_e(identifier["source_url"])}">Published identifier source ↗</a></dd></div>'
        if not p.get("identifiers"):
            body += '<div><dt>Published PIRR identifier</dt><dd>No identifier transcribed from the reviewed public account. The programme URL remains its source reference.</dd></div>'
        body += f'<div><dt>Public account / source</dt><dd><a href="{_e(p["url"])}">Read the complete programme record ↗</a> · Reviewed {_e(p["reviewed"])}</dd></div></dl>'
        if p.get("current_work"):
            body += f'<details><summary>Scope and current work from the public account</summary><p>{_e(p["current_work"])}</p></details>'
        if p.get("public_sources"):
            body += '<h3>Public records cited by this programme</h3><ul class="source-list">'
            for public in p["public_sources"]:
                body += f'<li><a href="{_e(public["url"])}">{_e(public["title"])} ↗</a><small>{_e(public["relation"])}</small></li>'
            body += '</ul>'
        neighbours = [rel for rel in data.get("programme_relations", []) if p["key"] in (rel["from"], rel["to"])]
        if neighbours:
            body += '<h3>Connected programmes</h3><ul class="source-list">'
            for rel in neighbours:
                other = rel["to"] if rel["from"] == p["key"] else rel["from"]
                body += f'<li><a href="#{_e(other)}">{_e(by_key[other]["title"])}</a><small>{_e(rel["relation"])} · <a href="{_e(rel["source_url"])}">Source relationship ↗</a></small></li>'
            body += '</ul>'
        body += f'<h3>Archive publications connected with this research <span class="catalogue-id">{len(related):02d}</span></h3>'
        if related:
            body += '<ul class="source-list registry-publications">' + ''.join(_publication(r, link) for r, link in related) + '</ul>'
        else:
            body += '<p>The selected archive has no work-specific programme relationship recorded here. The public account may include developing work and publications outside this deposited selection.</p>'
        body += '</article>'
    unlinked = [r for r in records if not r["pirr_references"]]
    if unlinked:
        body += ('<section class="item-section registry-record" data-registry-entry data-search="' + _e(' '.join(str(v) for r in unlinked for v in [r['title'], r.get('accession'), r.get('doi')])) + '"><div class="section-no">Publication identities / Additional research access</div><h2>Further publications in the archive</h2><p>These deposited publications remain searchable by DOI and archive reference. A work-specific programme relationship has not been asserted in the reviewed catalogue evidence.</p><ul class="source-list registry-publications">' + ''.join(_publication(r) for r in unlinked) + '</ul></section>')
    body += '</div><p id="registry-empty" hidden>No matching research references. Try a shorter identifier, a DOI or a word from the title.</p>'
    body += r'''<script>(function(){const input=document.getElementById('registry-search'),rows=Array.from(document.querySelectorAll('[data-registry-entry]')),status=document.getElementById('registry-results'),empty=document.getElementById('registry-empty');function run(){const terms=input.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);let count=0;rows.forEach(function(row){const text=row.dataset.search.toLocaleLowerCase();row.hidden=!terms.every(function(term){return text.includes(term)});if(!row.hidden)count++});status.textContent=count+' of '+rows.length+' research sections shown';empty.hidden=count>0}input.value=new URLSearchParams(location.search).get('q')||'';input.addEventListener('input',run);document.getElementById('registry-search-form').addEventListener('submit',function(e){e.preventDefault();run();const u=new URL(location.href);input.value.trim()?u.searchParams.set('q',input.value.trim()):u.searchParams.delete('q');history.replaceState(null,'',u)});document.getElementById('registry-reset').addEventListener('click',function(){input.value='';run();input.focus();const u=new URL(location.href);u.searchParams.delete('q');history.replaceState(null,'',u)});run()})();</script>'''
    schema = {"@context": "https://schema.org", "@type": "CollectionPage", "@id": origin.rstrip("/") + "/research-registry.html#crosswalk", "name": "PIRR research record crosswalk", "description": data["scope"], "isBasedOn": {"@id": data["registry_url"]}, "about": [{"@type": "ResearchProject", "@id": p["url"], "name": p["title"], "identifier": [{"@type": "PropertyValue", "propertyID": i["scheme"], "value": i["value"], "url": i["source_url"]} for i in p.get("identifiers", [])]} for p in data["programmes"]]}
    write("research-registry.html", layout("Research registry & publication references", "Search published PIRR project IDs and programme references; follow their source-qualified connections to deposited publications and chapter records.", body, path="research-registry.html", schema=schema))
    csv_out = StringIO()
    columns = ["programme_title", "programme_url", "identifier_scheme", "identifier", "identifier_source", "archive_reference", "publication_title", "edition_doi", "publication_record", "relation", "relation_note", "relation_source"]
    writer = csv.DictWriter(csv_out, fieldnames=columns)
    writer.writeheader()
    for r in records:
        relationships = deepcopy(r["pirr_references"])
        for link in relationships:
            link["registry_url"] = origin.rstrip("/") + "/" + link["registry_url"]
        components = [{"reference": part["reference"], "title": part["title"], "url": origin.rstrip("/") + "/" + part["url"], "reader_url": origin.rstrip("/") + "/" + part["reader_url"], "identifier_scheme": "Local analytic description reference", "programme_attribution": "Access through parent publication; no independent component-level programme relationship asserted."} for part in r.get("contents", [])]
        work = {**deepcopy(r["pirr_work_identity"]), "title": r["title"], "url": origin.rstrip("/") + f'/items/{r["id"]}.html', "programme_relationships": relationships, "components": components}
        export["publications"].append(work)
        for link in r["pirr_references"] or [{}]:
            for identifier in link.get("identifiers") or [{}]:
                writer.writerow({"programme_title": link.get("programme_title", ""), "programme_url": link.get("programme_url", ""), "identifier_scheme": identifier.get("scheme", ""), "identifier": identifier.get("value", ""), "identifier_source": identifier.get("source_url", ""), "archive_reference": r.get("accession", ""), "publication_title": r["title"], "edition_doi": work["edition_doi"], "publication_record": work["url"], "relation": link.get("relation", ""), "relation_note": link.get("relation_note", ""), "relation_source": link.get("source_url", "")})
    referenced = {link["programme_key"] for r in records for link in r["pirr_references"]}
    for programme in data["programmes"]:
        if programme["key"] in referenced:
            continue
        for identifier in programme.get("identifiers") or [{}]:
            writer.writerow({"programme_title": programme["title"], "programme_url": programme["url"], "identifier_scheme": identifier.get("scheme", ""), "identifier": identifier.get("value", ""), "identifier_source": identifier.get("source_url", ""), "relation_note": "No work-specific relationship to an item in this selected archive has been asserted."})
    write("data/research-crosswalk.json", json.dumps(export, ensure_ascii=False, indent=2) + "\n")
    write("data/research-crosswalk.csv", csv_out.getvalue())
    return ["research-registry.html"]
