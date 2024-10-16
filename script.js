function copyTextToClipboard(text, button) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    textarea.setSelectionRange(0, 99999);
    document.execCommand('copy');
    document.body.removeChild(textarea);
    const originalText = button.textContent;
    button.textContent = 'Copied!';
    setTimeout(() => {
        button.textContent = originalText;
    }, 2000);
}

// Отправляем данные на сервер
$(document).ready(function() {
    $('#jsonForm').on('submit', function(event) {
        event.preventDefault();
        $('#loader').removeClass('hidden');
        const formData = {
            field1: $('input[name="field1"]').val(),
            field2: $('textarea[name="field2"]').val()
        };
        $.ajax({
            type: 'POST',
            url: '/submit_json',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            success: function(response) {
                $('#result').fadeOut(200, function() {
                    $(this).html(response).fadeIn(200);
                });
                $('#jsonForm')[0].reset();
            },
            error: function(xhr) {
                $('#result').fadeOut(200, function() {
                    $('#result').html(xhr.responseText).fadeIn(200);
                });
            },
            complete: function() {
                $('#loader').addClass('hidden');
            }
        });
    });
});

// Принимаем данные с сервера
$(document).ready(function() {
    $('#FieldCopyTextForm').on('submit', function(event) {
        event.preventDefault();
        $('#loader2').removeClass('hidden');
        const field1Value = $('input[name="field1-copy-text-button"]').val();
        $.ajax({
            type: 'POST',
            url: '/get_field2',
            contentType: 'application/json',
            data: JSON.stringify({ field1: field1Value }),
            success: function(response) {
                // Создаем кнопку с параметром field2
                const button = $('<button>')
                    .text("Copy to clipboard")
                    .addClass('copy-button')
                    .attr('onclick', `copyTextToClipboard(${JSON.stringify(response.field2)}, this)`);
                $('input[name="field1-copy-text-button"]').val('');
                $('#result2').fadeOut(200, function() {
                    $(this).empty().append(button).fadeIn(200);
                });
            },
            error: function(xhr) {
                $('input[name="field1-copy-text-button"]').val('');
                $('#result2').fadeOut(200, function() {
                    $('#result2').html("<span style='color: red;'>Error:</span> " + xhr.responseJSON.message).fadeIn(200);
                });
            },
            complete: function() {
                $('#loader2').addClass('hidden');
            }
        });
    });
});

window.onload = function () {
    const year = new Date().getFullYear();
    document.getElementById("current-year").textContent = year;
};