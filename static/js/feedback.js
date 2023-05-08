$(document).ready(function() {
  'use strict'

  const forms = document.querySelectorAll('.needs-validation')

  Array.from(forms).forEach(form => {
      console.log(form)
    form.addEventListener('submit', event => {
      if(!form.checkValidity()) {
        event.preventDefault()
        event.stopPropagation()
      }

      form.classList.add('was-validated')
    }, false)
  })

  $(".first-input").focus();
})
