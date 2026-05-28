document.getElementById("buscarProducto").addEventListener("keyup", function() {
    let filtro = this.value.toLowerCase();
    let filas = document.querySelectorAll("table tbody tr");

    filas.forEach(fila => {
        let texto = fila.innerText.toLowerCase();
        fila.style.display = texto.includes(filtro) ? "" : "none";
    });
});