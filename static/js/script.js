const hamBurger = document.querySelector(".toggle-btn");

hamBurger.addEventListener("click", function () {
  // Alterna la clase 'expand' en el sidebar
  document.querySelector("#sidebar").classList.toggle("expand");

  // Cierra cualquier dropdown abierto
  const collapseElements = document.querySelectorAll('.collapse.show');
  collapseElements.forEach(function (collapse) {
    collapse.classList.remove('show');
  });
});

