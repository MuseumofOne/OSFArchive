// Keep each search control in the same DOM and keyboard order as its mobile layout.
(() => {
  const tree = document.querySelector('.archive-workspace > .collection-tree');
  const catalogueSearch = document.getElementById('catalogue-search')?.closest('.searchbar');
  const form = document.querySelector('.research-discovery > [data-discovery-form]');
  const search = catalogueSearch || form;
  if (!tree || !search) return;

  const workbench = tree.nextElementSibling;
  const filters = document.querySelector('.catalogue-layout > .filters');
  const results = catalogueSearch?.parentElement;
  const compact = window.matchMedia('(max-width: 760px)');

  function placeSearch() {
    const focused = document.activeElement;
    if (compact.matches) {
      if (catalogueSearch) filters.before(catalogueSearch);
      search.after(tree);
    } else if (tree.nextElementSibling !== workbench) {
      workbench.before(tree);
      if (catalogueSearch) results.prepend(catalogueSearch);
    }
    if (focused !== document.activeElement && focused?.isConnected) {
      focused.focus({preventScroll: true});
    }
  }

  placeSearch();
  compact.addEventListener('change', placeSearch);
})();
