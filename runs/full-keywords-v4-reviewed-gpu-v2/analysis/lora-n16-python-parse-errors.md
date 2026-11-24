# Seed 0 LoRA N=16 · Python HumanEval parse errors

Of 164 tasks, 142 ended in a parse error, 14 parsed without the required entry point, 6 executed and failed, and 2 passed. Each row below reproduces the saved parser error using the project extractor and Python 3.12. The category follows the location Python actually rejected. A row can have additional defects. The attempt column identifies the response used for the recorded final score.

| First reported cause | Tasks | Share of parse errors |
|---|---:|---:|
| Function header missing def | 120 | 84.5% |
| String cut off at token cap | 6 | 4.2% |
| Prose selected as code | 5 | 3.5% |
| Mismatched brackets or parentheses | 4 | 2.8% |
| Colon after assignment | 3 | 2.1% |
| Literal end marker in code | 1 | 0.7% |
| Unclosed Markdown fence | 1 | 0.7% |
| Invalid call used as block header | 1 | 0.7% |
| Synthetic keyword repeated in comprehension | 1 | 0.7% |

For the 120 missing-def cases, adding only that keyword on the flagged line made 71 parse. Of those, 69 defined the expected top-level function. This checks syntax and function names only. The original scores are unchanged.

Of the 142 final errors, 36 occurred on the initial response and 106 on the retry. Of the retries, 56 stopped naturally and 50 reached their token budget. A token cap alone does not establish why a snippet failed.

## All affected tasks

Task links identify the line in the consolidated result log. Long source lines are abbreviated.

| HumanEval ID | Primary cause | Parser line and excerpt | Attempt / finish | Additional finding |
|---:|---|---|---|---|
| [0](../results.jsonl:3095) | Function header missing def | 3 · <code>has_close_elements(numbers, threshold):</code> | Initial / stop | Adding def parses and yields the required function. |
| [1](../results.jsonl:3096) | String cut off at token cap | 31 · <code>res = re.findall(r&#x27;\((?:[^()]*&#124;\((</code> | Retry / length | Final generation ended inside the quoted value. A function header also omits def. |
| [2](../results.jsonl:3097) | Function header missing def | 3 · <code>truncate_number(number: float) -&gt; float:</code> | Initial / stop | Adding def parses and yields the required function. |
| [3](../results.jsonl:3098) | Function header missing def | 4 · <code>below_zero(operations: List[int]) -&gt; bool:</code> | Initial / stop | Adding def parses and yields the required function. |
| [4](../results.jsonl:3099) | Function header missing def | 3 · <code>mean_absolute_deviation(numbers):</code> | Initial / stop | Adding def parses and yields the required function. |
| [5](../results.jsonl:3100) | Prose selected as code | 1 · <code>Wait, I think I&#x27;m getting confused again. Let me start fresh:</code> | Retry / length | Last matched fence block contained commentary. |
| [6](../results.jsonl:3101) | Mismatched brackets or parentheses | 8 · <code>res = [max([level]) + patterns[-1])</code> | Retry / length | A function header also omits def. |
| [7](../results.jsonl:3102) | Prose selected as code | 1 · <code>Actually, I think I&#x27;m confusing myself. Let me write the complete solution properly:</code> | Retry / length | Last matched fence block contained commentary. |
| [8](../results.jsonl:3103) | Function header missing def | 3 · <code>sum_product(numbers: List[int]) -&gt; Tuple[int, int]:</code> | Initial / stop | Adding def parses and yields the required function. |
| [10](../results.jsonl:3105) | String cut off at token cap | 6 · <code>pattern = &#x27;abababababababababababababababababababababababababababababababab … abababababababababababababab</code> | Retry / length | Final generation ended inside the quoted value. A function header also omits def. |
| [11](../results.jsonl:3106) | Mismatched brackets or parentheses | 10 · <code>res = &#x27;&#x27;.join([str(int(&#x27;&#x27;.join([str(int(str(x)))))])</code> | Retry / stop |  |
| [12](../results.jsonl:3107) | Function header missing def | 4 · <code>longest(strings: List[str]) -&gt; Optional[str]:</code> | Initial / stop | Adding def parses and yields the required function. |
| [13](../results.jsonl:3108) | Function header missing def | 3 · <code>greatest_common_divisor(a: int, b: int) -&gt; int:</code> | Initial / stop | Adding def parses and yields the required function. |
| [14](../results.jsonl:3109) | Literal end marker in code | 5 · <code>&lt;&#124;endoftext&#124;&gt;!</code> | Retry / length |  |
| [15](../results.jsonl:3110) | Colon after assignment | 3 · <code>n = int(n):</code> | Retry / stop |  |
| [16](../results.jsonl:3111) | Function header missing def | 3 · <code>count_distinct_characters(string):</code> | Retry / stop | Adding def exposes line 7: invalid syntax. |
| [17](../results.jsonl:3112) | Function header missing def | 3 · <code>parse_music(music_string: str) -&gt; List[int]:</code> | Retry / stop | Adding def exposes line 10: invalid syntax. |
| [18](../results.jsonl:3113) | Function header missing def | 3 · <code>how_many_times(string: str, substring: str) -&gt; int:</code> | Retry / length | Adding def exposes line 5: invalid syntax. |
| [19](../results.jsonl:3114) | Unclosed Markdown fence | 1 · <code>```python</code> | Retry / length | No complete fence pair; the opening backticks reached the parser. |
| [20](../results.jsonl:3115) | Function header missing def | 3 · <code>find_closest_elements(numbers: list[float]) -&gt; tuple[float, float]:</code> | Retry / stop | Adding def parses and yields the required function. |
| [21](../results.jsonl:3116) | Function header missing def | 3 · <code>rescale_to_unit(numbers: List[float]) -&gt; List[float]:</code> | Retry / length | Adding def exposes line 56: '[' was never closed. |
| [22](../results.jsonl:3117) | Function header missing def | 3 · <code>filter_integers(values: List[Any]) -&gt; List[int]:</code> | Initial / stop | Adding def parses and yields the required function. |
| [24](../results.jsonl:3119) | Prose selected as code | 1 · <code>The correct solution is:</code> | Retry / length | Last matched fence block contained commentary. |
| [25](../results.jsonl:3120) | Function header missing def | 3 · <code>factorize(n: int) -&gt; List[int]:</code> | Retry / stop | Adding def parses and yields the required function. |
| [26](../results.jsonl:3121) | Function header missing def | 3 · <code>remove_duplicates(numbers: List[int]) -&gt; List[int]:</code> | Retry / stop | Adding def parses and yields the required function. |
| [28](../results.jsonl:3123) | Function header missing def | 3 · <code>concatenate(strings: List[str]) -&gt; str:</code> | Initial / stop | Adding def parses and yields the required function. |
| [29](../results.jsonl:3124) | Function header missing def | 3 · <code>filter_by_prefix(strings: List[str], prefix: str) -&gt; List[str]:</code> | Retry / stop | Adding def parses and yields the required function. |
| [30](../results.jsonl:3125) | Function header missing def | 3 · <code>get_positive(l):</code> | Retry / stop | Adding def parses and yields the required function. |
| [31](../results.jsonl:3126) | Function header missing def | 3 · <code>is_prime(n):</code> | Initial / stop | Adding def parses and yields the required function. |
| [32](../results.jsonl:3127) | Function header missing def | 3 · <code>find_zero(xs):</code> | Initial / stop | Adding def parses and yields the required function. |
| [34](../results.jsonl:3129) | Function header missing def | 3 · <code>unique(l: list):</code> | Retry / stop | Adding def parses and yields the required function. |
| [35](../results.jsonl:3130) | Function header missing def | 3 · <code>max_element(l):</code> | Retry / stop | Adding def parses and yields the required function. |
| [36](../results.jsonl:3131) | Function header missing def | 3 · <code>fizz_buzz(n):</code> | Retry / length | Adding def exposes line 4: invalid syntax. Perhaps you forgot a comma?. |
| [38](../results.jsonl:3133) | Function header missing def | 3 · <code>encode_cyclic(s: str):</code> | Retry / length | Adding def parses, but the required function is absent. |
| [39](../results.jsonl:3134) | Function header missing def | 3 · <code>is_prime(x):</code> | Retry / length | Adding def parses, but the required function is absent. |
| [40](../results.jsonl:3135) | Function header missing def | 3 · <code>triples_sum_to_zero(l):</code> | Retry / length | Adding def exposes line 63: '(' was never closed. |
| [42](../results.jsonl:3137) | Function header missing def | 1 · <code>incr_list(l: list):</code> | Initial / stop | Adding def parses and yields the required function. |
| [43](../results.jsonl:3138) | Function header missing def | 4 · <code>pairs_sum_to_zero(l):</code> | Retry / stop | Adding def exposes line 6: invalid syntax. |
| [44](../results.jsonl:3139) | Function header missing def | 3 · <code>change_base(x: int, base: int):</code> | Retry / stop | Adding def parses and yields the required function. |
| [45](../results.jsonl:3140) | Function header missing def | 3 · <code>triangle_area(a, h):</code> | Initial / stop | Adding def parses and yields the required function. |
| [48](../results.jsonl:3143) | Function header missing def | 3 · <code>is_palindrome(text: str):</code> | Retry / stop | Adding def parses and yields the required function. |
| [49](../results.jsonl:3144) | Function header missing def | 3 · <code>modp(n: int, p: int):</code> | Initial / stop | Adding def parses and yields the required function. |
| [50](../results.jsonl:3145) | Function header missing def | 3 · <code>decode_shift(s: str):</code> | Retry / stop | Adding def parses and yields the required function. |
| [51](../results.jsonl:3146) | Function header missing def | 3 · <code>remove_vowels(text):</code> | Retry / stop | Adding def parses and yields the required function. |
| [52](../results.jsonl:3147) | Function header missing def | 3 · <code>below_threshold(l, t):</code> | Retry / stop | Adding def exposes line 4: invalid syntax. |
| [53](../results.jsonl:3148) | Function header missing def | 3 · <code>add(x: int, y: int):</code> | Initial / stop | Adding def parses and yields the required function. |
| [54](../results.jsonl:3149) | Function header missing def | 3 · <code>same_chars(s0: str, s1: str):</code> | Retry / stop | Adding def exposes line 6: invalid syntax. |
| [55](../results.jsonl:3150) | Function header missing def | 3 · <code>fib(n: int):</code> | Initial / stop | Adding def parses and yields the required function. |
| [56](../results.jsonl:3151) | Function header missing def | 3 · <code>correct_bracketing(brackets: str):</code> | Retry / length | Adding def parses and yields the required function. |
| [57](../results.jsonl:3152) | Function header missing def | 3 · <code>monotonic(l):</code> | Retry / stop | Adding def parses and yields the required function. |
| [58](../results.jsonl:3153) | Function header missing def | 3 · <code>common(l1, l2):</code> | Retry / length | Adding def exposes line 4: invalid syntax. |
| [59](../results.jsonl:3154) | Function header missing def | 3 · <code>largest_prime_factor(n):</code> | Initial / stop | Adding def parses and yields the required function. |
| [60](../results.jsonl:3155) | Function header missing def | 1 · <code>sum_to_n(n: int):</code> | Initial / stop | Adding def parses and yields the required function. |
| [61](../results.jsonl:3156) | Function header missing def | 3 · <code>correct_bracketing(brackets: str):</code> | Retry / stop | Adding def exposes line 18: invalid syntax. |
| [62](../results.jsonl:3157) | Function header missing def | 3 · <code>derivative(xs):</code> | Retry / length | Adding def parses and yields the required function. |
| [63](../results.jsonl:3158) | Function header missing def | 3 · <code>fibfib(n: int):</code> | Retry / stop | Adding def exposes line 34: invalid syntax. |
| [64](../results.jsonl:3159) | Function header missing def | 5 · <code>vowels_count(s):</code> | Initial / stop | Adding def parses and yields the required function. |
| [65](../results.jsonl:3160) | Function header missing def | 3 · <code>circular_shift(x, shift):</code> | Retry / length | Adding def exposes line 6: invalid syntax. |
| [66](../results.jsonl:3161) | Function header missing def | 3 · <code>digitSum(s):</code> | Retry / stop | Adding def parses and yields the required function. |
| [67](../results.jsonl:3162) | Function header missing def | 3 · <code>fruit_distribution(s, n):</code> | Retry / stop | Adding def parses and yields the required function. |
| [69](../results.jsonl:3164) | Function header missing def | 3 · <code>search(lst):</code> | Initial / stop | Adding def parses and yields the required function. |
| [70](../results.jsonl:3165) | Function header missing def | 3 · <code>strange_sort_list(lst):</code> | Retry / length | Adding def exposes line 100: '(' was never closed. |
| [72](../results.jsonl:3167) | Function header missing def | 3 · <code>will_it_fly(q, w):</code> | Retry / length | Adding def exposes line 6: invalid syntax. |
| [74](../results.jsonl:3169) | Function header missing def | 3 · <code>total_match(lst1, lst2):</code> | Retry / stop | Adding def parses and yields the required function. |
| [75](../results.jsonl:3170) | Function header missing def | 3 · <code>is_multiply_prime(a):</code> | Initial / stop | Adding def parses and yields the required function. |
| [76](../results.jsonl:3171) | Function header missing def | 3 · <code>is_simple_power(x, n):</code> | Initial / stop | Adding def exposes line 6: invalid syntax. |
| [77](../results.jsonl:3172) | Function header missing def | 3 · <code>iscube(x):</code> | Initial / stop | Adding def parses and yields the required function. |
| [78](../results.jsonl:3173) | Function header missing def | 3 · <code>hex_key(num):</code> | Initial / stop | Adding def exposes line 22: invalid syntax. |
| [79](../results.jsonl:3174) | Prose selected as code | 1 · <code>Let me write it cleanly:</code> | Retry / length | Last matched fence block contained commentary. |
| [80](../results.jsonl:3176) | String cut off at token cap | 5 · <code>sub = list(re.finditer(&#x27;abababababababababababababababababababababababababa … abababababababababababababab</code> | Retry / length | Final generation ended inside the quoted value. A function header also omits def. |
| [81](../results.jsonl:3175) | Function header missing def | 3 · <code>numerical_letter_grade(grades):</code> | Retry / stop | Adding def parses and yields the required function. |
| [82](../results.jsonl:3178) | Function header missing def | 3 · <code>prime_length(string):</code> | Retry / length | Adding def exposes line 7: invalid syntax. |
| [83](../results.jsonl:3177) | Function header missing def | 3 · <code>starts_one_ends(n):</code> | Retry / stop | Adding def parses and yields the required function. |
| [85](../results.jsonl:3180) | Function header missing def | 3 · <code>add(lst):</code> | Retry / stop | Adding def exposes line 4: invalid syntax. Perhaps you forgot a comma?. |
| [86](../results.jsonl:3182) | Function header missing def | 3 · <code>anti_shuffle(text):</code> | Retry / length | Adding def exposes line 62: '(' was never closed. |
| [87](../results.jsonl:3181) | Function header missing def | 3 · <code>get_row(lst, x):</code> | Retry / stop | Adding def exposes line 5: invalid syntax. |
| [88](../results.jsonl:3183) | Function header missing def | 3 · <code>sort_array(array):</code> | Retry / stop | Adding def exposes line 6: invalid syntax. |
| [90](../results.jsonl:3186) | Function header missing def | 3 · <code>next_smallest(lst):</code> | Retry / length | Adding def exposes line 8: '(' was never closed. |
| [91](../results.jsonl:3185) | Mismatched brackets or parentheses | 5 · <code>count = sum([pattern == &#x27;I love this weather&#x27;] for pattern in patterns)]</code> | Retry / stop | A function header also omits def. |
| [93](../results.jsonl:3188) | Function header missing def | 3 · <code>encode(message):</code> | Retry / stop | Adding def parses and yields the required function. |
| [94](../results.jsonl:3189) | Function header missing def | 3 · <code>skjkasdkd(lst):</code> | Retry / length | Adding def exposes line 85: '[' was never closed. |
| [95](../results.jsonl:3190) | Function header missing def | 3 · <code>check_dict_case(dict):</code> | Retry / stop | Adding def exposes line 5: invalid syntax. |
| [96](../results.jsonl:3191) | Function header missing def | 3 · <code>count_up_to(n):</code> | Retry / length | Adding def parses and yields the required function. |
| [97](../results.jsonl:3192) | Function header missing def | 3 · <code>multiply(a, b):</code> | Retry / stop | Adding def parses and yields the required function. |
| [98](../results.jsonl:3195) | Function header missing def | 3 · <code>count_upper(s):</code> | Retry / length | Adding def exposes line 4: invalid syntax. |
| [99](../results.jsonl:3193) | Function header missing def | 3 · <code>closest_integer(value):</code> | Initial / stop | Adding def parses and yields the required function. |
| [101](../results.jsonl:3196) | Function header missing def | 3 · <code>words_string(s):</code> | Initial / stop | Adding def parses and yields the required function. |
| [102](../results.jsonl:3198) | Function header missing def | 3 · <code>choose_num(x, y):</code> | Retry / stop | Adding def parses and yields the required function. |
| [103](../results.jsonl:3197) | Function header missing def | 3 · <code>rounded_avg(n, m):</code> | Initial / stop | Adding def parses and yields the required function. |
| [104](../results.jsonl:3199) | Function header missing def | 3 · <code>unique_digits(x):</code> | Retry / length | Adding def exposes line 10: invalid syntax. |
| [105](../results.jsonl:3200) | Function header missing def | 3 · <code>by_length(arr):</code> | Retry / stop | Adding def parses and yields the required function. |
| [106](../results.jsonl:3201) | Colon after assignment | 3 · <code>n = range(1, n + 1):</code> | Retry / stop |  |
| [107](../results.jsonl:3202) | Function header missing def | 3 · <code>even_odd_palindrome(n):</code> | Retry / stop | Adding def parses and yields the required function. |
| [108](../results.jsonl:3203) | Function header missing def | 3 · <code>count_nums(arr):</code> | Retry / stop | Adding def parses and yields the required function. |
| [109](../results.jsonl:3204) | Function header missing def | 3 · <code>move_one_ball(arr):</code> | Retry / stop | Adding def exposes line 8: invalid syntax. |
| [112](../results.jsonl:3207) | Function header missing def | 3 · <code>reverse_delete(s, c):</code> | Retry / length | Adding def exposes line 40: invalid syntax. |
| [113](../results.jsonl:3208) | String cut off at token cap | 5 · <code>patterns = &#x27;n&#x27;, &#x27;strn&#x27;, &#x27;ngn&#x27;, &#x27;ngn&#x27;, &#x27;ngn&#x27;, &#x27;n&#x27;, &#x27;n&#x27;, &#x27;n&#x27;, &#x27;n&#x27;, &#x27;n&#x27;, &#x27;n&#x27;,  … , &#x27;n&#x27;, &#x27;n&#x27;, &#x27;n&#x27;, &#x27;n&#x27;, &#x27;n&#x27;, &#x27;</code> | Retry / length | Final generation ended inside the quoted value. A function header also omits def. |
| [114](../results.jsonl:3209) | Function header missing def | 3 · <code>minSubArraySum(nums):</code> | Retry / stop | Adding def parses and yields the required function. |
| [115](../results.jsonl:3210) | Function header missing def | 3 · <code>max_fill(grid, capacity):</code> | Retry / stop | Adding def parses and yields the required function. |
| [116](../results.jsonl:3211) | Function header missing def | 3 · <code>sort_array(arr):</code> | Retry / length | Adding def exposes line 61: '(' was never closed. |
| [117](../results.jsonl:3212) | Function header missing def | 3 · <code>select_words(s, n):</code> | Retry / length | Adding def exposes line 95: '[' was never closed. |
| [118](../results.jsonl:3213) | String cut off at token cap | 67 · <code>patterns_indices = list(re.finditer(&#x27;([aeiouAEIOU])</code> | Retry / length | Final generation ended inside the quoted value. A function header also omits def. |
| [119](../results.jsonl:3214) | Function header missing def | 3 · <code>match_parens(lst):</code> | Retry / length | Adding def exposes line 52: '(' was never closed. |
| [121](../results.jsonl:3216) | Function header missing def | 3 · <code>solution(lst):</code> | Retry / stop | Adding def parses and yields the required function. |
| [122](../results.jsonl:3217) | Function header missing def | 3 · <code>add_elements(arr, k):</code> | Retry / length | Adding def exposes line 37: '[' was never closed. |
| [123](../results.jsonl:3218) | Function header missing def | 3 · <code>get_odd_collatz(n):</code> | Retry / stop | Adding def exposes line 10: invalid syntax. |
| [124](../results.jsonl:3219) | Function header missing def | 3 · <code>valid_date(date):</code> | Retry / stop | Adding def exposes line 5: invalid syntax. |
| [125](../results.jsonl:3220) | Function header missing def | 3 · <code>split_words(txt):</code> | Retry / stop | Adding def parses and yields the required function. |
| [126](../results.jsonl:3221) | Function header missing def | 3 · <code>is_sorted(lst):</code> | Retry / stop | Adding def exposes line 6: invalid syntax. |
| [127](../results.jsonl:3222) | Function header missing def | 3 · <code>is_prime(n):</code> | Retry / stop | Adding def exposes line 4: invalid syntax. |
| [128](../results.jsonl:3223) | Function header missing def | 3 · <code>prod_signs(arr):</code> | Retry / stop | Adding def parses and yields the required function. |
| [129](../results.jsonl:3224) | Invalid call used as block header | 13 · <code>dfs(start_positions, grid, k, [], directions):</code> | Retry / stop | The colon follows a call containing the literal [] as an argument; adding def would still leave invalid parameters. |
| [131](../results.jsonl:3226) | Function header missing def | 3 · <code>digits(n):</code> | Retry / length | Adding def exposes line 49: '(' was never closed. |
| [132](../results.jsonl:3228) | Function header missing def | 3 · <code>is_nested(string):</code> | Retry / length | Adding def exposes line 5: invalid syntax. |
| [133](../results.jsonl:3227) | Function header missing def | 3 · <code>sum_squares(lst):</code> | Initial / stop | Adding def parses and yields the required function. |
| [134](../results.jsonl:3229) | Function header missing def | 3 · <code>check_if_last_char_is_a_letter(txt):</code> | Retry / length | Adding def exposes line 4: invalid syntax. |
| [135](../results.jsonl:3230) | Function header missing def | 3 · <code>can_arrange(arr):</code> | Retry / length | Adding def exposes line 9: invalid syntax. |
| [136](../results.jsonl:3231) | Function header missing def | 3 · <code>largest_smallest_integers(lst):</code> | Initial / stop | Adding def parses and yields the required function. |
| [137](../results.jsonl:3232) | Function header missing def | 3 · <code>compare_one(a, b):</code> | Retry / stop | Adding def exposes line 5: invalid syntax. |
| [138](../results.jsonl:3233) | Function header missing def | 3 · <code>is_equal_to_sum_even(n):</code> | Retry / stop | Adding def exposes line 5: invalid syntax. |
| [139](../results.jsonl:3234) | Function header missing def | 3 · <code>special_factorial(n):</code> | Initial / stop | Adding def parses and yields the required function. |
| [140](../results.jsonl:3236) | Function header missing def | 3 · <code>fix_spaces(text):</code> | Retry / length | Adding def parses and yields the required function. |
| [141](../results.jsonl:3235) | Function header missing def | 3 · <code>file_name_check(file_name):</code> | Initial / stop | Adding def exposes line 4: invalid syntax. |
| [142](../results.jsonl:3237) | Function header missing def | 3 · <code>sum_squares(lst):</code> | Initial / stop | Adding def parses and yields the required function. |
| [144](../results.jsonl:3239) | Colon after assignment | 8 · <code>patterns = re.compile(r&#x27;^(\d+)/(\d+$):&#x27;):</code> | Retry / length |  |
| [145](../results.jsonl:3240) | Mismatched brackets or parentheses | 4 · <code>res = sorted(range(len(nums)), key=lambda i: (sum(map(str, map(int, str(abs(nums[i])))))), nums[i]))</code> | Retry / stop | A function header also omits def. |
| [146](../results.jsonl:3241) | Function header missing def | 3 · <code>specialFilter(nums):</code> | Retry / length | Adding def exposes line 5: invalid syntax. |
| [147](../results.jsonl:3242) | Synthetic keyword repeated in comprehension | 6 · <code>count = sum([1 for i nu nu nu nu nu nu nu nu nu nu nu nu nu nu nu nu nu nu  … u nu nu nu nu nu nu nu nu nu</code> | Retry / length | The seed-0 spelling of in (nu) repeats after for i. |
| [148](../results.jsonl:3243) | Prose selected as code | 1 · <code>Wait, I&#x27;m getting confused. Let me simplify:</code> | Retry / length | Last matched fence block contained commentary. |
| [149](../results.jsonl:3244) | Function header missing def | 3 · <code>sorted_list_sum(lst):</code> | Retry / stop | Adding def parses and yields the required function. |
| [150](../results.jsonl:3247) | Function header missing def | 3 · <code>x_or_y(n, x, y):</code> | Retry / length | Adding def exposes line 16: invalid syntax. |
| [151](../results.jsonl:3245) | Function header missing def | 3 · <code>double_the_difference(lst):</code> | Initial / stop | Adding def parses and yields the required function. |
| [152](../results.jsonl:3246) | Function header missing def | 3 · <code>compare(game, guess):</code> | Initial / stop | Adding def parses and yields the required function. |
| [153](../results.jsonl:3248) | Function header missing def | 3 · <code>Strongest_Extension(class_name, extensions):</code> | Retry / length | Adding def exposes line 4: invalid syntax. |
| [154](../results.jsonl:3249) | String cut off at token cap | 40 · <code>patterns = re.findall(r&#x27;b*ab*&#x27;, patterns + &#x27;ab*ab*ab</code> | Retry / length | Final generation ended inside the quoted value. A function header also omits def. |
| [155](../results.jsonl:3252) | Function header missing def | 3 · <code>even_odd_count(num):</code> | Retry / length | Adding def parses and yields the required function. |
| [156](../results.jsonl:3250) | Function header missing def | 1 · <code>int_to_mini_roman(number):</code> | Initial / stop | Adding def parses and yields the required function. |
| [157](../results.jsonl:3251) | Function header missing def | 3 · <code>right_angle_triangle(a, b, c):</code> | Initial / stop | Adding def exposes line 18: invalid syntax. |
| [158](../results.jsonl:3253) | Function header missing def | 3 · <code>find_max(words):</code> | Retry / stop | Adding def parses and yields the required function. |
| [159](../results.jsonl:3254) | Function header missing def | 3 · <code>eat(number, need, remaining):</code> | Retry / length | Adding def exposes line 8: invalid syntax. |
| [160](../results.jsonl:3255) | Function header missing def | 3 · <code>do_algebra(operator, operand):</code> | Retry / stop | Adding def parses and yields the required function. |
| [162](../results.jsonl:3257) | Function header missing def | 3 · <code>string_to_md5(text):</code> | Retry / stop | Adding def parses and yields the required function. |
