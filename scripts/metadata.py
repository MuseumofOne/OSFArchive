"""Source-qualified catalogue exports; no network access or source mutation.

The catalogue description is distinct from the deposited edition and its files.
Qualified Dublin Core XML is an application export, not an OAI-PMH response.
"""
from __future__ import annotations

from relationship_metadata import extend_graph, relationship_assertions
from descriptions import repository_description_text
from identities import (work_uri, responsibility_uri, institutional_target,
                        institutional_scope, edition_isbn)
import mimetypes
import re
from typing import Any
import xml.etree.ElementTree as ET


DC = "http://purl.org/dc/elements/1.1/"
DCT = "http://purl.org/dc/terms/"
CAT = "urn:museum-of-one:catalogue:metadata:1:"


def _doi(value: Any) -> str:
    value = str(value or "").strip()
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value, flags=re.I)
    return "https://doi.org/" + value if value else ""


def _orcid(value: Any) -> str:
    value = str(value or "").strip().removeprefix("https://orcid.org/")
    return "https://orcid.org/" + value if re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", value) else ""


def assertion(field: str, value: Any, source_url: str | None,
              status: str = "source_transcription", note: str = "",
              reviewed: str | None = None) -> dict:
    """Construct a qualified field assertion, without asserting verification.

    A source URL identifies evidence, not agreement or endorsement by that source.
    Callers can replace generated defaults with reviewed per-field assertions.
    """
    result = {"field": field, "value": value, "status": status}
    if source_url:
        result["source_url"] = source_url
    if note:
        result["note"] = note
    if reviewed:
        result["reviewed"] = reviewed
    return result


def build_assertions(r: dict) -> list[dict]:
    """Default provenance for the normalized catalogue contract.

    Only r.source_created/source_modified are repository timestamps. A review date
    is a local catalogue review date. Neither is the first-publication date.
    Explicit r.field_assertions entries take precedence for the same field.
    """
    source = r.get("zenodo_url")
    institution = r.get("institutional_url")
    reviewed = r.get("source_review") or r.get("reviewed")
    results = []

    def add(field, value, url=source, status="source_transcription", note=""):
        if value not in (None, "", [], {}):
            results.append(assertion(field, value, url, status, note, reviewed))

    add("title", r.get("title"), institution or source, "catalogue_title",
        "Local display title; the deposited title is retained separately.")
    for field in ("source_title", "doi", "date", "version", "conceptdoi", "creators",
                  "keywords", "language", "license", "rights", "files",
                  "source_created", "source_modified"):
        add(field, r.get(field))
    for field in ("record_created", "record_modified"):
        provenance = r.get(field + "_provenance") or {}
        add(field, r.get(field), None, provenance.get("status") or "local_catalogue_lifecycle",
            provenance.get("note") or "Explicit local catalogue lifecycle date; not an original-work, publication or repository-record date.")
    add("source_review", reviewed, None, "catalogue_source_review",
        "Review of descriptive sources; not the creation or modification date of the work or repository record.")
    for field in ("author", "publisher", "first_edition", "edition_statement", "isbn"):
        add(field, r.get(field), institution or source, "institutional_context",
            "Consult the linked edition record; a repository version is not a new book edition."
            if field in ("first_edition", "edition_statement", "isbn") else "Institutional responsibility statement; original repository creator roles remain separate.")
    add("orcid", r.get("orcid"), institution or source, "source_linked_identifier",
        "Creator identifier supplied by the linked sources; no affiliation or endorsement is inferred.")
    if r.get('orcid_authority'):
        authority = r['orcid_authority']
        results.append(assertion('orcid_authority', authority, authority.get('url'),
                                 authority.get('status', 'source_linked_identifier'),
                                 authority.get('access_note', ''), authority.get('reviewed')))
    add("summary", r.get("summary"), institution or source, "editorial_enrichment",
        "Catalogue-editor summary based on the linked work; not an original publisher abstract.")
    add("subjects", r.get("subjects"), institution or source, "editorial_enrichment",
        "Local discovery terms; no controlled-vocabulary assignment is claimed.")
    add("collection", r.get("collection"), None, "editorial_grouping",
        "A local browsing collection, not an original repository collection.")
    add("corroboration", r.get("corroboration"), institution, "catalogue_review_note")
    add("discrepancies", r.get("discrepancies"), institution or source, "catalogue_review_note")
    add("alternate_titles", r.get("alternate_titles"), institution or source, "source_qualified_title_variants", "Each variant retains its own source and scope; a web page title is not a title-page transcription.")
    add("date_precision", r.get("date_precision"), source, "derived_from_source", "Precision reported exactly as supplied; missing month or day is not filled.")
    for field in ("medium", "digital_formats", "extent", "digital_extent"):
        add(field, r.get(field), source, "derived_from_source", "Digital medium and extent derived from repository file metadata; no physical custody is implied. MIME may be inferred from filename. Repository checksums are transcribed; reading-copy verification, where available, is recorded separately.")
    add("identifier_validation", r.get("identifier_validation"), source, "local_syntax_validation", "Checksum/syntax validation does not verify registration, assignment or edition applicability.")
    add("source_identifiers", r.get("source_identifiers"), source, "source_transcription", "Retained source identifiers with applicability notes; not automatically identifiers of this item.")
    add("contributor_roles", r.get("contributor_roles"), source, "source_transcription", "Creator and contributor roles are transcribed, not inferred from names or affiliations.")
    add("serial", r.get("serial"), source, "source_declared_relationship", "Serial context is attached only where the repository declares the ISSN relationship.")
    add("authority_links", r.get("authority_links"), institution, "source_qualified_external_context", "External records have separate status and edition scope; links are not endorsements or equivalence assertions.")
    for programme in r.get("research_programmes") or []:
        add("research_programme:" + programme.get("url", ""), programme, programme.get("source_url") or institution, "institutional_work_relationship", "Programme relationship and stage follow the work-specific institutional badge; publication does not imply a completed programme or collaboration.")
    results.extend(relationship_assertions(r))
    explicit = r.get("field_assertions") or []
    if isinstance(explicit, list):
        override = {x.get("field") for x in explicit if isinstance(x, dict)}
        results = [x for x in results if x["field"] not in override]
        results.extend(x for x in explicit if isinstance(x, dict) and x.get("field"))
    return results


def _kind(r: dict) -> str:
    typ = str(r.get("type") or "").lower()
    if "book" in typ or r.get("collection") == "Books & volumes":
        return "Book"
    if "dataset" in typ:
        return "Dataset"
    if "photograph" in typ or "image" in typ and "moving" not in typ:
        return "Photograph"
    if "moving image" in typ or "video" in typ:
        return "VideoObject"
    if "sound" in typ or "audio" in typ:
        return "AudioObject"
    if "article" in typ:
        return "ScholarlyArticle"
    return "CreativeWork"


def build_graph(r: dict, itemurl: str, origin: str) -> dict:
    """schema.org graph for a local record and the deposited edition it describes."""
    origin = origin.rstrip("/")
    itemurl = itemurl.split("#", 1)[0]
    edition_id = _doi(r.get("doi")) or itemurl + "#edition"
    family_id = _doi(r.get("conceptdoi"))
    source_url = r.get("zenodo_url")
    institution_url = r.get("institutional_url")
    author_name = r.get("author")
    orcid = _orcid(r.get("orcid"))
    author_id = responsibility_uri(r, 'author', origin)
    publisher_id = responsibility_uri(r, 'publisher', origin)
    work_id = work_uri(r, origin)
    catalogue_id = itemurl + "#catalogue-record"
    webpage_id = itemurl + "#webpage"
    graph = [
        {"@type": "WebSite", "@id": origin + "/#website",
         "name": "Museum of One Digital Archive Library", "url": origin + "/"},
        {"@type": "WebPage", "@id": webpage_id, "url": itemurl,
         "name": r.get("title", "Catalogue record"),
         "isPartOf": {"@id": origin + "/#website"},
         "mainEntity": {"@id": catalogue_id}, "about": {"@id": edition_id}},
    ]
    catalogue = {
        "@type": "CreativeWork", "@id": catalogue_id,
        "name": r.get("title", "Catalogue record"),
        "url": itemurl, "mainEntityOfPage": {"@id": webpage_id},
        "about": {"@id": edition_id},
        "disambiguatingDescription": "Local catalogue record describing a deposited publication version.",
    }
    if r.get("summary"):
        catalogue["description"] = r["summary"]
    if r.get("subjects"):
        catalogue["keywords"] = r["subjects"]
    if r.get("accession") or r.get("id"):
        catalogue["identifier"] = {"@type": "PropertyValue", "propertyID": "Local catalogue identifier",
                                   "value": r.get("accession") or str(r["id"])}
    if r.get("record_created"):
        catalogue["dateCreated"] = r["record_created"]
    if r.get("record_modified"):
        catalogue["dateModified"] = r["record_modified"]
    if r.get("source_review") or r.get("reviewed"):
        graph[1]["lastReviewed"] = r.get("source_review") or r["reviewed"]
    sources = [{"@id": u} for u in (source_url, institution_url) if u]
    if sources:
        catalogue["isBasedOn"] = sources
    graph.append(catalogue)

    work = {"@type": "CreativeWork", "@id": work_id,
            "name": r.get("title") or r.get("source_title"),
            "description": "Local work identity, distinct from its deposited editions, repository version family and catalogue description."}
    if r.get('isbn') and not edition_isbn(r):
        work['identifier'] = {"@type": "PropertyValue", "propertyID": "Source-reported title-level ISBN",
                              "value": r['isbn'], "description": "Edition/format applicability remains unresolved; not exported as the deposited edition's ISBN."}
    graph.append(work)

    edition = {"@type": _kind(r), "@id": edition_id,
               "name": r.get("source_title") or r.get("title") or "Deposited publication",
               "mainEntityOfPage": {"@id": source_url} if source_url else {"@id": webpage_id}}
    if source_url:
        edition["url"] = source_url
    if r.get("doi"):
        edition["identifier"] = {"@type": "PropertyValue", "propertyID": "DOI", "value": _doi(r["doi"]).removeprefix("https://doi.org/")}
    if r.get("source_title") and r.get("source_title") != r.get("title"):
        edition["alternateName"] = r.get("title")
    if r.get("date"):
        edition["datePublished"] = r["date"]
    if r.get("version"):
        edition["version"] = str(r["version"])
    if r.get("language"):
        edition["inLanguage"] = r["language"]
    if r.get("keywords"):
        edition["keywords"] = r["keywords"]
    if author_name:
        edition["author"] = {"@id": author_id}
        author = {"@type": "Person", "@id": author_id, "name": author_name}
        if orcid:
            author["identifier"] = {"@type": "PropertyValue", "propertyID": "ORCID", "value": orcid.rsplit("/", 1)[-1]}
        graph.append(author)
    if r.get("publisher"):
        publisher_name = str(r["publisher"])
        edition["publisher"] = {"@id": publisher_id}
        publisher = {"@type": "Organization", "@id": publisher_id, "name": publisher_name}
        if "museum of one" in publisher_name.lower():
            publisher["url"] = "https://www.museumofone.art/"
        graph.append(publisher)
    if edition_isbn(r) and edition["@type"] == "Book":
        edition["isbn"] = edition_isbn(r)
    if r.get("alternate_titles"):
        edition["alternateName"] = [t["title"] for t in r["alternate_titles"] if t.get("kind") != "institutional_web_record_title"]
    edition_statement = r.get("edition_statement") or (r.get("institutional_metadata") or {}).get("edition")
    if edition_statement and edition["@type"] == "Book":
        edition["bookEdition"] = edition_statement
    if r.get("source_abstract"):
        edition["abstract"] = r["source_abstract"]
    source_description = repository_description_text(r)
    if source_description:
        edition["description"] = source_description[:5000]
    if edition["@type"] == "ScholarlyArticle":
        edition["headline"] = edition["name"]
    if r.get("cover"):
        edition["image"] = origin + "/" + r["cover"].lstrip("/")
    license_ = r.get("license") or {}
    if isinstance(license_, dict) and license_.get("url"):
        edition["license"] = license_["url"]
    if r.get("rights"):
        edition["copyrightNotice"] = r["rights"]
    if family_id and family_id != edition_id:
        edition["exampleOfWork"] = {"@id": family_id}
        graph.append({"@type": "CreativeWork", "@id": family_id,
                      "name": (r.get("title") or "Publication") + " — version family",
                      "identifier": {"@type": "PropertyValue", "propertyID": "Zenodo concept DOI",
                                     "value": family_id.removeprefix("https://doi.org/")},
                      "exampleOfWork": {"@id": work_id}, "workExample": {"@id": edition_id}})
        work['workExample'] = {'@id': family_id}
    else:
        edition['exampleOfWork'] = {'@id': work_id}
        work['workExample'] = {'@id': edition_id}
    # Only map relationships whose schema.org meaning matches the source label.
    # Other source relationships remain intact in JSON/XML provenance exports.
    for relation in r.get("relations") or []:
        if not isinstance(relation, dict):
            continue
        label = relation.get("relation") or relation.get("relation_type") or ""
        target = relation.get("url") or relation.get("identifier") or ""
        if not target:
            continue
        if str(relation.get("scheme", "")).lower() == "doi":
            target = _doi(target)
        if not str(target).startswith(("https://", "http://")):
            continue
        prop = {"ispartof": "isPartOf", "haspart": "hasPart", "references": "citation",
                "isderivedfrom": "isBasedOn", "isbasedon": "isBasedOn"}.get(re.sub(r"[^a-z]", "", label.lower()))
        if prop:
            edition.setdefault(prop, []).append({"@id": target})
    files = []
    for i, file in enumerate(r.get("files") or []):
        if not isinstance(file, dict) or not file.get("url"):
            continue
        fid = itemurl + "#file-" + str(i + 1)
        media = {"@type": "DataDownload" if edition["@type"] == "Dataset" else "MediaObject", "@id": fid, "contentUrl": file["url"],
                 "name": file.get("name") or "Repository file", "encodesCreativeWork": {"@id": edition_id}}
        mime = file.get("mimetype") or file.get("mime_type") or mimetypes.guess_type(file.get("name", ""))[0]
        if mime:
            media["encodingFormat"] = mime
        size = file.get("size")
        if isinstance(size, (int, float)):
            media["contentSize"] = str(size) + " bytes"
        elif file.get("size_label"):
            media["contentSize"] = file["size_label"]
        if file.get("checksum"):
            media["identifier"] = {"@type": "PropertyValue", "propertyID": "Source checksum", "value": file["checksum"]}
        files.append({"@id": fid})
        graph.append(media)
    if files:
        edition["encoding"] = files
        if edition["@type"] == "Dataset":
            edition["distribution"] = list(files)
    serial = r.get("serial")
    if serial:
        serial_id = serial["url"]
        edition.setdefault("isPartOf", []).append({"@id": serial_id})
        graph.append({"@type": "Periodical", "@id": serial_id, "name": serial["title"], "issn": serial["issn"], "url": serial_id})
    # Editorial discovery terms belong to the catalogue record, not the source's controlled vocabulary.
    term_refs=[]
    from urllib.parse import quote
    for subject in r.get("subjects") or []:
        term_id=origin+"/subjects.html#term-"+quote(subject, safe="")
        graph.append({"@type":"DefinedTerm","@id":term_id,"name":subject,"inDefinedTermSet":{"@id":origin+"/subjects.html#local-discovery-vocabulary"}})
        term_refs.append({"@id":term_id})
    if term_refs:
        catalogue["about"]=[{"@id":edition_id}]+term_refs
        graph.append({"@type":"DefinedTermSet","@id":origin+"/subjects.html#local-discovery-vocabulary","name":"Museum of One local editorial discovery vocabulary","description":"Catalogue-editor discovery terms; not an assignment from an external controlled vocabulary."})
    # Programme links describe the work's documented research context. They are not coauthorship assertions.
    for index, programme in enumerate(r.get("research_programmes") or []):
        programme_id=programme.get("url")
        if not programme_id: continue
        graph.append({"@type":"WebPage","@id":programme_id,"url":programme_id,"name":programme.get("title"),"description":programme.get("relation_label") or programme.get("relation") or "Institutional research context"})
        catalogue.setdefault("isBasedOn",[]).append({"@id":programme.get("source_url") or programme_id})
        catalogue.setdefault("mentions",[]).append({"@id":programme_id})
    # Source roles are represented without guessing that every named organization is a person.
    for index, role in enumerate(r.get("contributor_roles") or []):
        if role.get("source_category")!="contributor" or not role.get("name"):continue
        role_id=itemurl+"#source-role-"+str(index+1)
        entity_id=itemurl+"#source-contributor-"+str(index+1)
        entity_type="Organization" if "museum" in role["name"].lower() or role.get("source_role") in ("HostingInstitution","RegistrationAgency","RegistrationAuthority","ResearchGroup") else "Person"
        graph.append({"@type":entity_type,"@id":entity_id,"name":role["name"]})
        graph.append({"@type":"Role","@id":role_id,"roleName":role.get("source_role") or "Contributor (role not supplied)","contributor":{"@id":entity_id}})
        edition.setdefault("contributor",[]).append({"@id":role_id})
    graph.append({"@type":"BreadcrumbList","@id":itemurl+"#breadcrumb","itemListElement":[{"@type":"ListItem","position":1,"name":"Digital Archive Library","item":origin+"/"},{"@type":"ListItem","position":2,"name":"Catalogue","item":origin+"/catalogue.html"},{"@type":"ListItem","position":3,"name":r.get("accession") or r.get("title"),"item":itemurl}]})
    graph[1]["breadcrumb"]={"@id":itemurl+"#breadcrumb"}
    reading=r.get("reading_copy")
    if reading:
        access_id=origin+"/assets/documents/"+str(r["id"])+".pdf"
        access={"@type":"MediaObject","@id":access_id,"contentUrl":access_id,"name":"Verified reading copy of "+str(r.get("title")),"encodingFormat":"application/pdf","contentSize":str(reading["bytes"])+" bytes","description":str(reading["page_count"])+" PDF file pages, including covers and unnumbered pages. Byte-identical local access copy; source checksum matched "+reading["verified_at"]+".","encodesCreativeWork":{"@id":edition_id},"isBasedOn":{"@id":itemurl+"#file-1"},"identifier":{"@type":"PropertyValue","propertyID":"SHA-256 of local reading copy","value":reading["sha256"]}}
        if isinstance(r.get("license"),dict) and r["license"].get("url"):access["license"]=r["license"]["url"]
        graph.append(access);edition.setdefault("encoding",[]).append({"@id":access_id})
    if r.get("osf_copy"):
        o = r["osf_copy"]
        osf_id = o["osf_url"] + "#file"
        graph.append({"@type": "MediaObject", "@id": osf_id, "url": o["osf_url"],
                      "contentUrl": o["osf_download_url"], "encodingFormat": "application/pdf",
                      "name": r["title"] + " — exact edition PDF on OSF",
                      "contentSize": str(o["bytes"]) + " bytes",
                      "encodesCreativeWork": {"@id": edition_id},
                      "identifier": {"@type": "PropertyValue", "propertyID": "SHA-256", "value": o["sha256"]},
                      "description": "Byte-identical access copy verified " + o["verified_at"] + ". Deposit timestamps are not publication dates; consult the file's rights notices."})
        edition.setdefault("encoding", []).append({"@id": osf_id})
    graph.append(edition)
    if source_url:
        source = {"@type": "WebPage", "@id": source_url,
                  "name": "Zenodo deposited-version record", "mainEntity": {"@id": edition_id},
                  "publisher": {"@id": "https://zenodo.org/#repository"}}
        if r.get("source_created"):
            source["dateCreated"] = r["source_created"]
        if r.get("source_modified"):
            source["dateModified"] = r["source_modified"]
        graph.extend([source, {"@type": "Organization", "@id": "https://zenodo.org/#repository",
                               "name": "Zenodo", "url": "https://zenodo.org/"}])
    if institution_url:
        graph.append({"@type": "WebPage", "@id": institution_url,
                      "name": "Museum of One institutional publication context",
                      "description": "Reviewed relationship scope: " + institutional_scope(r).replace('_', ' '),
                      "about": {"@id": institutional_target(r, origin)}})
    return extend_graph({"@context": "https://schema.org", "@graph": graph},r,itemurl,origin)


def build_dc(r: dict) -> str:
    """Qualified DC application export, with explicit local provenance extensions."""
    for prefix, ns in (("dc", DC), ("dcterms", DCT), ("cat", CAT)):
        ET.register_namespace(prefix, ns)
    root = ET.Element("{" + CAT + "}record", {"profile": "qualified-dublin-core-with-catalogue-provenance", "version": "2"})

    def add(term, value, namespace=DCT, origin=None):
        if value in (None, "", [], {}):
            return
        values = value if isinstance(value, list) else [value]
        for v in values:
            el = ET.SubElement(root, "{" + namespace + "}" + term)
            el.text = str(v)
            if origin:
                el.set("{" + CAT + "}origin", origin)

    # This record describes the selected repository edition, with local enrichment.
    add("title", r.get("title"), origin="catalogue_display")
    if r.get("source_title") and r["source_title"] != r.get("title"):
        add("alternative", r["source_title"], origin="repository_title")
    add("creator", r.get("author"), origin="institutional_responsibility")
    add("publisher", r.get("publisher"), origin="institutional_context")
    add("issued", r.get("date"), origin="repository_publication_date")
    # The top-level DC description concerns the deposited edition. Repository
    # and local catalogue lifecycle dates therefore use explicitly scoped terms.
    add("repositoryRecordCreated", r.get("source_created"), namespace=CAT, origin="repository_record_creation")
    add("repositoryRecordModified", r.get("source_modified"), namespace=CAT, origin="repository_record_modification")
    add("recordCreated", r.get("record_created"), namespace=CAT, origin="local_catalogue_lifecycle")
    add("recordModified", r.get("record_modified"), namespace=CAT, origin="local_catalogue_lifecycle")
    add("sourceReviewDate", r.get("source_review") or r.get("reviewed"), namespace=CAT, origin="catalogue_source_review")
    add("identifier", _doi(r.get("doi")), origin="repository_version")
    add("identifier", r.get("accession") or str(r.get("id") or ""), origin="local_catalogue")
    if edition_isbn(r):
        add("identifier", "ISBN " + edition_isbn(r), origin="evidenced_edition_format_identifier")
    elif r.get("isbn"):
        add("titleLevelISBN", r["isbn"], namespace=CAT, origin="source_reported_title_identifier_format_unresolved")
    add("source", r.get("zenodo_url"), origin="repository_record")
    add("references", r.get("institutional_url"), origin="institutional_corroboration")
    if r.get("osf_copy"):
        add("hasFormat", r["osf_copy"]["osf_url"], origin="sha256_verified_exact_edition_access_copy")
    add("isVersionOf", _doi(r.get("conceptdoi")), origin="repository_version_family")
    add("type", r.get("type"), origin="catalogue_resource_type")
    add("language", r.get("language"), origin="repository_metadata")
    add("description", r.get("summary"), origin="editorial_summary")
    add("subject", r.get("subjects"), origin="editorial_local_vocabulary")
    add("subject", r.get("keywords"), origin="repository_keywords")
    lic = r.get("license") or {}
    if isinstance(lic, dict):
        add("license", lic.get("url") or lic.get("label"), origin="repository_edition_licence")
    add("rights", r.get("rights"), origin="repository_rights_notice")
    if r.get("version"):
        add("version", r["version"], namespace=CAT, origin="repository_version_label")
    if r.get("first_edition"):
        add("editionStatement", r["first_edition"], namespace=CAT, origin="institutional_context")
    if r.get("edition_statement"):
        add("editionStatement", r["edition_statement"], namespace=CAT, origin="institutional_context")
    for title in r.get("alternate_titles") or []:
        add("alternative", title.get("title"), origin=title.get("kind"))
    add("extent", r.get("extent"), origin="derived_repository_file_metadata")
    add("format", (r.get("digital_extent") or {}).get("formats"), origin="source_or_inferred_file_format")
    add("medium", r.get("medium"), origin="derived_digital_medium")
    for contributor in r.get("contributor_roles") or []:
        if contributor.get("source_category")=="contributor":
            add("contributor", contributor.get("name")+(" ["+contributor["source_role"]+"]" if contributor.get("source_role") else ""), origin="repository_contributor_role")
    for programme in r.get("research_programmes") or []:
        add("relation", programme.get("url"), origin="institutional_research_context")
    if r.get("serial"):
        add("isPartOf", r["serial"]["url"], origin="repository_declared_serial_relation")
    for file in r.get("files") or []:
        if isinstance(file, dict) and file.get("url"):
            add("hasFormat", file["url"], origin="repository_file")
    for part in r.get("contents") or []:
        add("hasPart", part.get("url"), origin="source_verified_local_analytic_description")
    for entity in r.get("entity_links") or []:
        add("relation", entity.get("label")+" ["+entity.get("relation", "related")+"]", origin="source_qualified_entity_relationship")
    for term in r.get("controlled_subjects") or []:
        add("subject", term.get("uri"), origin="maintained_local_controlled_vocabulary")
    for rel in r.get("relations") or []:
        if isinstance(rel, dict):
            relvalue = rel.get("identifier") or rel.get("url")
            relname = rel.get("relation") or rel.get("relation_type") or "relation"
            mapping = {"isversionof": "isVersionOf", "hasversion": "hasVersion", "ispartof": "isPartOf", "haspart": "hasPart", "references": "references", "isreferencedby": "isReferencedBy", "isformatof": "isFormatOf", "hasformat": "hasFormat"}
            add(mapping.get(re.sub(r"[^a-z]", "", relname.lower()), "relation"), relvalue, origin="source_relation")
    add("provenance", "Repository metadata, institutional publication context, and catalogue-editor enrichment are distinguished below. Repository dates are not assertions of first publication; repository version labels do not establish new book editions.")
    assertions = ET.SubElement(root, "{" + CAT + "}assertions")
    for item in build_assertions(r):
        attrs = {"field": item["field"], "status": item.get("status", "unspecified")}
        entry = ET.SubElement(assertions, "{" + CAT + "}assertion", attrs)
        val = item.get("value")
        ET.SubElement(entry, "{" + CAT + "}value").text = str(val) if not isinstance(val, (dict, list)) else __import__("json").dumps(val, ensure_ascii=False)
        for key in ("source_url", "note", "reviewed"):
            if item.get(key):
                ET.SubElement(entry, "{" + CAT + "}" + key).text = item[key]
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)
