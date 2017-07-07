$(function(){
    var $write = $('#write'), $write2 = $('#Cmd_To_Send'),
		shift = false,
		capslock = false;
	
	$('#keyboard li').click(function(){
		var $this = $(this),
			character = $this.html(); // If it's a lowercase letter, nothing happens to this variable
		
		// Shift keys
		if ($this.hasClass('left-shift') || $this.hasClass('right-shift')) {
			$('.letter').toggleClass('uppercase');
			$('.symbol span').toggle();
			
			shift = (shift === true) ? false : true;
			capslock = false;
			return false;
		}
		
		// Caps lock
		if ($this.hasClass('capslock')) {
			$('.letter').toggleClass('uppercase');
			capslock = true;
			return false;
		}
		
		// Delete
		if ($this.hasClass('delete')) {
		    var text = $write[0].value;
			
		    $write[0].value = text.substr(0, text.length - 1);
			return false;
		}
		
		// Special characters
		if ($this.hasClass('symbol')) character = $('span:visible', $this).html();
		if ($this.hasClass('space')) character = ' ';
		if ($this.hasClass('tab')) character = "\t";
		if ($this.hasClass('return')) character = "";
		
		// Uppercase letter
		if ($this.hasClass('uppercase')) character = character.toUpperCase();
		
		// Remove shift once a key is clicked.
		if (shift === true) {
			$('.symbol span').toggle();
			if (capslock === false) $('.letter').toggleClass('uppercase');
			
			shift = false;
		}
		
	    // Add the character
		$write[0].value = $write[0].value + character;
	});
	$('#keyboard2 li').click(function () {
	    var $this = $(this),
			character = $this.html(); // If it's a lowercase letter, nothing happens to this variable

	    // Shift keys
	    if ($this.hasClass('left-shift') || $this.hasClass('right-shift')) {
	        $('.letter').toggleClass('uppercase');
	        $('.symbol span').toggle();

	        shift = (shift === true) ? false : true;
	        capslock = false;
	        return false;
	    }

	    // Caps lock
	    if ($this.hasClass('capslock')) {
	        $('.letter').toggleClass('uppercase');
	        capslock = true;
	        return false;
	    }

	    // Delete
	    if ($this.hasClass('delete')) {
	        var text2 = $write2[0].value;

	        $write2[0].value = text2.substr(0, text2.length - 1);
	        return false;
	    }

	    // Special characters
	    if ($this.hasClass('symbol')) character = $('span:visible', $this).html();
	    if ($this.hasClass('space')) character = ' ';
	    if ($this.hasClass('tab')) character = "\t";
	    if ($this.hasClass('return')) character = "";

	    // Uppercase letter
	    if ($this.hasClass('uppercase')) character = character.toUpperCase();

	    // Remove shift once a key is clicked.
	    if (shift === true) {
	        $('.symbol span').toggle();
	        if (capslock === false) $('.letter').toggleClass('uppercase');

	        shift = false;
	    }

	    // Add the character
	    $write2[0].value = $write2[0].value + character;
	});
});