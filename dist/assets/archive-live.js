/* Keep the native catalogue aligned with the same validated index as search.
 * No repository writes, deposits, publication approval or CMS mutations occur.
 * Publication identities must match their canonical item URLs. Supplemental
 * edition metadata remains explicitly a bundled baseline, never inferred.
 */
(function (root, factory) {
    'use strict';
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    else {
        root.MuseumArchiveLive = api;
        const start = () => root.document.querySelectorAll('[data-archive-explorer]').forEach(api.mount);
        if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', start, {once: true});
        else start();
    }
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
    'use strict';
    const ORIGIN = 'https://archive.museumofone.art';
    const SITE = 'https://www.museumofone.art';
    const mounted = new WeakMap();
    const text = value => typeof value === 'string' ? value : '';
    const texts = value => Array.isArray(value) ? value.filter(v => typeof v === 'string') : [];
    const unitLabel = (count, noun) => noun + (count === 1 ? '' : 's');
    const countLabel = (count, noun) => count + ' ' + unitLabel(count, noun);

    function catalogueRecords(payload, baseline = []) {
        if (!payload || payload.index_kind !== 'discovery' || payload.canonical_origin !== ORIGIN || !Array.isArray(payload.records)) {
            throw new Error('Invalid catalogue source');
        }
        const existing = new Map(baseline.map(record => [record.id, record]));
        const result = payload.records.filter(record => record.kind === 'publication').map(record => {
            const match = /^publication:(\d+)$/.exec(record.id);
            if (!match || record.url !== ORIGIN + '/items/' + match[1] + '.html' || !text(record.title)) {
                throw new Error('Publication identity does not match its item URL');
            }
            const id = match[1], old = existing.get(id) || {}, ids = texts(record.identifiers);
            const scopes = record.identifier_scopes || {};
            const doi = ids.find(value => /^10\.\d{4,9}\/\S+$/.test(value) && scopes[value] === 'Deposited edition DOI')
                || (ids.includes(old.doi) ? old.doi : '');
            const conceptdoi = ids.find(value => /^10\.\d{4,9}\/\S+$/.test(value) && /^Concept DOI\b/.test(scopes[value] || ''))
                || (ids.includes(old.conceptdoi) ? old.conceptdoi : '');
            const web = (record.relationships || []).find(edge => {
                try {
                    const url = new URL(edge.url);
                    return edge.relation === 'institutional web description' && url.origin === SITE
                        && !url.username && !url.password && !url.search && !url.hash;
                } catch { return false; }
            });
            const date = typeof record.date === 'string' && /^\d{4}(?:-\d{2}){0,2}$/.test(record.date) ? record.date : '';
            return {
                ...old,
                id,
                accession: ids.find(value => /^MOO-CAT-\d+$/.test(value)) || old.accession || id,
                title: record.title,
                short_title: old.title === record.title ? old.short_title || record.title : record.title,
                author: text(record.author),
                date,
                date_precision: date ? ({4: 'year', 7: 'month', 10: 'day'}[date.length]) : '',
                type: text(record.resource_type),
                collection: text(record.collection) || 'Other publications',
                summary: text(record.summary),
                subjects: texts(record.subjects),
                doi, conceptdoi,
                institutional_url: web ? web.url : text(old.institutional_url),
                catalogue_url: record.url,
                search_text: text(record.search_text),
                // No new ISBN, licence, page count, or PDF availability is guessed.
                metadata_scope: 'Discovery description; supplementary edition fields, where present, are bundled metadata. Consult the item record for current rights and files.'
            };
        });
        if (new Set(result.map(record => record.id)).size !== result.length) throw new Error('Duplicate publication identity');
        return result.sort((a, b) => a.accession.localeCompare(b.accession, 'en', {numeric: true}) || a.id.localeCompare(b.id, 'en', {numeric: true}));
    }

    function collectionTotals(index, records, bundledTotals) {
        const editions = new Map();
        const website = new Map();
        const add = (counts, group) => counts.set(group, (counts.get(group) || 0) + 1);
        for (const record of records) add(editions, record.collection);
        for (const record of index.records) {
            if (record.kind !== 'website' || !record.archive_url || !text(record.collection)) continue;
            const included = typeof record.catalogue_record === 'boolean' ? record.catalogue_record
                : !(record.relationships || []).some(edge => edge.target_id.startsWith('publication:'));
            if (included) add(website, record.collection);
        }
        // The theme's HTML preserves its bundled release counts when older snapshots omit catalogue metadata.
        const published = bundledTotals || new Map(Object.entries(index.collection_counts || {}));
        const groups = new Set([...published.keys(), ...editions.keys(), ...website.keys()]);
        const totals = new Map();
        for (const group of groups) {
            const deposited = editions.get(group) || 0;
            const derived = deposited + (website.get(group) || 0);
            const reported = published.get(group);
            const verified = bundledTotals
                ? Number.isSafeInteger(reported) && reported >= derived
                : reported === derived;
            const total = verified ? reported : derived;
            if (total) totals.set(group, total);
        }
        return totals;
    }

    function mount(root) {
        if (mounted.has(root)) return mounted.get(root);
        const doc = root.ownerDocument, win = doc.defaultView;
        const explorer = win.ArchiveExplorer && win.ArchiveExplorer.mount(root);
        const discovery = win.MuseumResearchDiscovery, host = root.querySelector('[data-research-discovery]');
        if (!explorer || !discovery || !host) return;
        const baseline = explorer.records;
        const bundledTotals = new Map(Array.from(root.querySelectorAll('[data-ax-full-count]'),
            node => [node.dataset.axFullCount, Number(node.dataset.count)]));
        const make = (tag, className, value) => {
            const node = doc.createElement(tag);
            if (className) node.className = className;
            if (value !== undefined) node.textContent = value;
            return node;
        };
        const anchor = (label, href) => {
            const node = make('a', '', label);
            node.href = href;
            node.dataset.axHandoff = '';
            return node;
        };
        const itemURL = record => record.catalogue_url || ORIGIN + '/items/' + record.id + '.html';
        let status = root.querySelector('[data-ax-update-status]');
        if (!status) {
            status = make('p', root.dataset.standalone === 'true' ? 'ax-note sr-only' : 'ax-note');
            status.dataset.axUpdateStatus = '';
            status.setAttribute('role', 'status');
            status.setAttribute('aria-live', 'polite');
            root.querySelector('.ax-opening').append(status);
        }
        let catalogueValid = true, catalogueVersion = '', collectionAnchor;
        const statusMessages = {
            snapshot: 'Bundled catalogue loaded. Checking the archive for updates…',
            fresh: 'Latest available archive index loaded. Edition details and rights are maintained in each item record.',
            stale: 'The archive update check failed. Keeping the last verified live catalogue and website records.',
            offline: 'The live archive could not be reached. Showing the bundled catalogue and its release totals. Website search requires the live archive.',
            'snapshot-only': 'Showing the bundled catalogue in this local preview.',
            unavailable: 'The research index is unavailable. Showing the bundled catalogue; open the full archive to check for updates.'
        };
        function setStatus(value) {
            if (value === 'fresh' && !catalogueValid) value = 'unavailable';
            status.dataset.state = value;
            status.textContent = statusMessages[value] || statusMessages.unavailable;
        }
        function updateCard(card, record) {
            Object.assign(card.dataset, {
                axRecord: record.id, collection: record.collection, date: record.date,
                year: record.date.slice(0, 4), type: record.type, title: record.title,
                search: [record.title, record.short_title, record.accession, record.author, record.doi,
                    record.conceptdoi, record.summary, record.collection, record.search_text].join(' ')
            });
            const set = (selector, value) => { const node = card.querySelector(selector); if (node) node.textContent = value; };
            set('.ax-reference > span:first-child', record.accession);
            set('.ax-card-copy > .ax-label', [record.type, record.date].filter(Boolean).join(' · '));
            set('.ax-card-copy h3 a', record.short_title);
            set('.ax-card-author', record.author);
            set('.ax-card-summary', record.summary);
            set('.ax-type-cover strong', record.short_title);
            set('.ax-type-cover small', record.author);
            card.querySelectorAll('.ax-cover,.ax-card-copy h3 a').forEach(link => { link.href = itemURL(record); });
            const save = card.querySelector('[data-ax-save]');
            if (save) {
                save.dataset.axSave = record.id;
                save.setAttribute('aria-label', 'Save ' + record.title + ' to reading list');
            }
            return card;
        }
        function newCard(record) {
            const card = make('article', 'ax-card'), ref = make('div', 'ax-reference');
            ref.append(make('span', '', record.accession), make('span', '', 'Item record'));
            const cover = anchor('', itemURL(record)); cover.className = 'ax-cover';
            const type = make('div', 'ax-type-cover');
            type.append(make('span', '', 'Museum of One · Archival Library'), make('strong', '', record.short_title), make('small', '', record.author));
            cover.append(type);
            const copy = make('div', 'ax-card-copy'), title = make('h3'), actions = make('div', 'ax-card-actions');
            title.append(anchor(record.short_title, itemURL(record)));
            const save = make('button', '', '＋ Save'); save.type = 'button'; save.dataset.axSave = record.id; save.setAttribute('aria-pressed', 'false');
            actions.append(anchor('Item record ↗', itemURL(record)), save);
            copy.append(make('p', 'ax-label'), title, make('p', 'ax-card-author'), make('p', 'ax-card-summary'), actions);
            card.append(ref, cover, copy);
            return updateCard(card, record);
        }
        function facet(name, values) {
            const select = root.querySelector('[data-ax-filter] select[name="' + name + '"]'), selected = select.value;
            const first = select.options[0].cloneNode(true);
            select.replaceChildren(first, ...values.map(value => { const option = make('option', '', value); option.value = value; return option; }));
            select.value = values.includes(selected) ? selected : '';
        }
        function applyIndex(index, source) {
            discovery.validateIndex(index, ORIGIN);
            const records = catalogueRecords(index, baseline), ids = new Set(records.map(record => record.id));
            const totals = collectionTotals(index, records, source === 'snapshot' ? bundledTotals : null);
            const nextCatalogue = JSON.stringify(records);
            const catalogueChanged = catalogueVersion !== nextCatalogue;
            const collections = [...totals.keys()];
            const grid = root.querySelector('[data-ax-cards]');
            if (catalogueChanged) {
            const current = new Map(Array.from(grid.children).map(card => [card.dataset.axRecord, card]));
            grid.replaceChildren(...records.map(record => current.has(record.id) ? updateCard(current.get(record.id), record) : newCard(record)));
            root.querySelectorAll('.ax-featured [data-ax-record]').forEach(card => {
                const record = records.find(item => item.id === card.dataset.axRecord);
                if (record) updateCard(card, record); else card.remove();
            });
            facet('collection', collections.filter(collection => records.some(record => record.collection === collection)));
            facet('year', [...new Set(records.map(record => record.date.slice(0, 4)).filter(Boolean))].sort().reverse());
            facet('type', [...new Set(records.map(record => record.type).filter(Boolean))].sort());
            }
            const tree = root.querySelector('.ax-tree nav');
            const oldGroups = new Map(Array.from(tree.querySelectorAll('.ax-tree-group')).map(group => [group.dataset.axCollectionGroup || group.querySelector('[data-ax-collection]')?.dataset.axCollection, group.open]));
            tree.querySelectorAll('.ax-tree-group').forEach(group => group.remove());
            const before = tree.querySelector('[data-ax-view="discover"]');
            // Standalone categories precede its tabs; native categories belong to
            // the overview panel. Keep each host's original visual placement.
            const panel = root.querySelector('.ax-entrance-collections') || root.querySelector('[data-ax-panel="overview"]');
            const previousRows = Array.from(panel.querySelectorAll('.ax-collection-row'));
            if (!collectionAnchor?.isConnected) {
                collectionAnchor = doc.createComment('Archive collection register');
                if (previousRows.length) previousRows[0].before(collectionAnchor);
                else (panel.querySelector('.ax-count-note') || panel.querySelector('.ax-section-head')).after(collectionAnchor);
            }
            previousRows.forEach(row => row.remove());
            let lastRow = collectionAnchor;
            let catalogueTotal = 0;
            collections.forEach((collection, number) => {
                const members = records.filter(record => record.collection === collection);
                const total = totals.get(collection);
                catalogueTotal += total;
                const methodology = collection === 'Methodology';
                const href = ORIGIN + (methodology ? '/methodology.html' : '/catalogue.html?collection=' + encodeURIComponent(collection));
                const details = make('details', 'ax-tree-group'), summary = make('summary', '', collection);
                details.open = oldGroups.get(collection) || false;
                details.dataset.axCollectionGroup = collection;
                const editionCount = countLabel(members.length, 'deposited edition');
                const catalogueCount = countLabel(total, 'catalogue record');
                const sidebarCount = make('small', 'ax-tree-total', catalogueCount);
                sidebarCount.dataset.axSidebarCount = collection;
                const sidebarBreakdown = make('small', 'ax-tree-breakdown', editionCount + ' · ' + countLabel(total - members.length, 'website record'));
                sidebarBreakdown.dataset.axSidebarBreakdown = collection;
                summary.append(sidebarCount, sidebarBreakdown);
                const browse = anchor('Browse all ' + countLabel(total, 'record') + ' ↗', href);
                browse.className = 'ax-tree-browse';
                const list = make('ul');
                members.forEach(record => {
                    const row = make('li'), link = anchor('', itemURL(record));
                    link.append(make('small', '', record.accession), doc.createTextNode(record.short_title));
                    row.append(link); list.append(row);
                });
                details.append(summary, browse, make('p', 'ax-tree-list-label', 'Deposited editions'), list); tree.insertBefore(details, before);
                const row = make('a', 'ax-collection-row'); row.href = href;
                const label = make('span');
                const breakdown = make('small');
                const depositNumber = make('span', '', members.length);
                const websiteNumber = make('span', '', total - members.length);
                depositNumber.dataset.axDepositCount = collection;
                websiteNumber.dataset.axWebsiteCount = collection;
                breakdown.append(depositNumber, ' ' + unitLabel(members.length, 'deposited edition') + ' · ',
                    websiteNumber, ' ' + unitLabel(total - members.length, 'website record'));
                label.append(make('strong', '', collection), breakdown);
                const count = make('span', 'ax-collection-count', catalogueCount + ' ↗');
                count.dataset.axFullCount = collection;
                count.dataset.count = total;
                const sequence = make('span', '', String(number + 1).padStart(2, '0'));
                sequence.setAttribute('aria-hidden', 'true');
                row.append(sequence, label, count);
                lastRow.after(row); lastRow = row;
            });
            const counts = {publication: records.length, catalogue: catalogueTotal, website: catalogueTotal - records.length,
                chapter: 0, entity: 0, programme: 0, collection: collections.length};
            index.records.forEach(record => { if (['chapter', 'entity', 'programme'].includes(record.kind)) counts[record.kind]++; });
            // Counts are derived, not trusted from optional feed count metadata.
            root.querySelectorAll('[data-ax-total]').forEach(node => { node.textContent = counts[node.dataset.axTotal] ?? ''; });
            doc.querySelectorAll('[data-archive-total]').forEach(node => { node.textContent = counts[node.dataset.archiveTotal] ?? ''; });
            const breakdownUnits = {publication: 'deposited edition', website: 'website record'};
            root.querySelectorAll('[data-ax-unit]').forEach(node => {
                const key = node.dataset.axUnit;
                node.textContent = unitLabel(counts[key], breakdownUnits[key]);
            });
            const summary = root.querySelector('.ax-tree > details > summary > small');
            if (summary) summary.textContent = countLabel(catalogueTotal, 'catalogue record') + ' · ' + countLabel(records.length, 'deposited edition');
            // Website-only captures update the collection counts without clearing
            // a reader's deposited-edition comparison or moving its cards.
            if (catalogueChanged) { explorer.updateRecords(records); catalogueVersion = nextCatalogue; }
            catalogueValid = true;
            return {records: records.length, ids};
        }
        host.addEventListener('museum:research-index', event => {
            try { applyIndex(event.detail.index, event.detail.source); } catch { catalogueValid = false; setStatus('unavailable'); }
        });
        host.addEventListener('museum:research-index-status', event => setStatus(event.detail.status));
        const handle = discovery.mount(host);
        if (handle?.index) {
            const source = handle.status === 'fresh' ? 'remote' : 'snapshot';
            try { applyIndex(handle.index, source); } catch { catalogueValid = false; setStatus('unavailable'); }
        }
        if (handle?.status) setStatus(handle.status);
        const controller = {applyIndex, setStatus};
        mounted.set(root, controller);
        return controller;
    }
    return {catalogueRecords, mount};
});
