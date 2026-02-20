## Updates after work began

- Do not worry about numbers. They always preceed "gold" and I don't care about gold. 


## Original Doc

Implement screen reading for a loot screenshot. 

This will get incoroporated into the bot, for now you have tests to work with. 

Our approach will be using template letters saved in @templates/letters/

# Tests 

We wrote test cases earlier that are memorialized in @test_ocr.py

# Approach 

I have done this before, for an older version of Diablo 2 with lower resolution. You can read my code at: https://github.com/eqmvii/python-bot-test

You don't have to do it the same way, but it could help you think about your plan. 

In general, you need to use the template letters to scan the image and determine where the letters are. That will then give you something like a coordinate grid that you can use to infer words and phrases. 

It is probably ideal to do some kind of greyscale conversion so your white and yellow template letters can find yellow, gold, etc. items. You may have to experiment there. 

The final output, as memorialized in the tests, should be a list of items and colors. Please also record the x, y coordinate of the center of each item that you find. 

# Philosophy

You don't need to get every letter to match perfectly. It's OK for there to be gaps in letters or wrong letters. As in the repo I linked above, levenshtein distance and a list of possible item names can get us the rest of the way there.

Don't obsess over details. It's important that you get a basic framework working that we can expand upon. Show me where you're at once you have promising results, I may be able to get you unstuck faster. 


