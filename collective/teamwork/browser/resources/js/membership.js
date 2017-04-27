/*jshint browser: true, nomen: false, eqnull: true, es5:true, trailing:true */

(function ($) {

  // For all cells, hookup unlock button in viewers column checkbox:
  function hookupUnlockViewers() {
    $('table.listing td a.unlock').click(
      function(event) {
        $(this).parent().children('.lockbox').show();
        $(this).parent().children('.checkmark').hide();
        $(this).hide();
      }
    );
  }

  function hookupGridModifiedHighlighting() {
    $('table.listing td input').click(function(event) {
      $(this).parent().addClass('modified');
      $(this).parent().parent().addClass('modified');
    });
  }

  function initMembership() {
    hookupUnlockViewers();
    hookupGridModifiedHighlighting();
    console.log('collective.teamwork membership management');  // TODO
  }

  $(document).ready(initMembership);

}(jQuery));
