# Synthetic HumanEval · seed 0, LoRA N=16

All 164 saved outcomes were audited. Each of the 150 parse failures was reproduced from the scored attempt with the project extractor and seed-0 decoder. Categories below take repetition first (at least five consecutive nu words), then identify the remaining failure. The last column independently records the scorer diagnostic.

The 128 repetitive answers had longest runs of 589–748 consecutive nu words (median 731). All used all 750 final-answer retry tokens. Of those 128 initial raw drafts, 115 already had at least five consecutive nu words. This comparison describes the trace; it does not establish what caused the repetitions.

| HumanEval ID | Classification | Evidence | Scorer diagnostic |
|---:|---|---|---|
| [0](../results.jsonl:2931) | Repeated nu | 720 consecutive nu words | invalid syntax |
| [1](../results.jsonl:2932) | Repeated nu | 715 consecutive nu words | invalid syntax |
| [2](../results.jsonl:2933) | Passed | truncate_number | passed |
| [3](../results.jsonl:2934) | Repeated nu | 727 consecutive nu words | invalid syntax |
| [4](../results.jsonl:2935) | Untranslated Python keyword | for | Untranslated Python syntax in synthetic output: for |
| [5](../results.jsonl:2936) | Repeated nu | 655 consecutive nu words | invalid syntax |
| [6](../results.jsonl:2937) | Repeated nu | 732 consecutive nu words | invalid syntax |
| [7](../results.jsonl:2938) | Repeated nu | 725 consecutive nu words | ('unexpected EOF in multi-line statement', (2, 0)) |
| [8](../results.jsonl:2939) | Repeated nu | 733 consecutive nu words | invalid syntax |
| [9](../results.jsonl:2940) | Repeated nu | 721 consecutive nu words | ('unexpected EOF in multi-line statement', (4, 0)) |
| [10](../results.jsonl:2941) | Repeated nu | 728 consecutive nu words | invalid syntax |
| [11](../results.jsonl:2942) | Repeated nu | 726 consecutive nu words | invalid syntax |
| [12](../results.jsonl:2943) | Repeated nu | 701 consecutive nu words | Untranslated Python syntax in synthetic output: if |
| [13](../results.jsonl:2944) | Execution failure | AssertionError | failed |
| [14](../results.jsonl:2945) | Repeated nu | 733 consecutive nu words | invalid syntax |
| [15](../results.jsonl:2946) | Untranslated Python keyword | for | Untranslated Python syntax in synthetic output: for |
| [16](../results.jsonl:2947) | Repeated nu | 730 consecutive nu words | ('unexpected EOF in multi-line statement', (2, 0)) |
| [17](../results.jsonl:2948) | Repeated nu | 724 consecutive nu words | invalid syntax |
| [18](../results.jsonl:2949) | Repeated nu | 724 consecutive nu words | invalid syntax |
| [19](../results.jsonl:2950) | Repeated nu | 737 consecutive nu words | invalid syntax |
| [20](../results.jsonl:2951) | Execution failure | NameError: name &#x27;List&#x27; is not defined. Did you mean: &#x27;list&#x27;? | failed |
| [21](../results.jsonl:2952) | Repeated nu | 732 consecutive nu words | invalid syntax |
| [22](../results.jsonl:2953) | Execution failure | NameError: name &#x27;List&#x27; is not defined. Did you mean: &#x27;list&#x27;? | failed |
| [23](../results.jsonl:2954) | Repeated nu | 735 consecutive nu words | invalid syntax |
| [24](../results.jsonl:2955) | Execution failure | AssertionError | failed |
| [25](../results.jsonl:2956) | Repeated nu | 702 consecutive nu words | invalid syntax |
| [26](../results.jsonl:2957) | Repeated nu | 730 consecutive nu words | invalid syntax |
| [27](../results.jsonl:2958) | Repeated nu | 729 consecutive nu words | invalid syntax |
| [28](../results.jsonl:2959) | Repeated nu | 721 consecutive nu words | ('unexpected EOF in multi-line statement', (4, 0)) |
| [29](../results.jsonl:2960) | Repeated nu | 725 consecutive nu words | ('unexpected EOF in multi-line statement', (2, 0)) |
| [30](../results.jsonl:2961) | Repeated nu | 735 consecutive nu words | invalid syntax |
| [31](../results.jsonl:2962) | Repeated nu | 728 consecutive nu words | invalid syntax |
| [32](../results.jsonl:2963) | Repeated nu | 728 consecutive nu words | invalid syntax |
| [33](../results.jsonl:2964) | Repeated nu | 723 consecutive nu words | invalid syntax |
| [34](../results.jsonl:2965) | Passed | unique | passed |
| [35](../results.jsonl:2966) | Repeated nu | 721 consecutive nu words | invalid syntax |
| [36](../results.jsonl:2967) | Repeated nu | 733 consecutive nu words | invalid syntax |
| [37](../results.jsonl:2968) | Repeated nu | 732 consecutive nu words | Untranslated Python syntax in synthetic output: for |
| [38](../results.jsonl:2969) | Repeated nu | 737 consecutive nu words | invalid syntax |
| [39](../results.jsonl:2970) | Repeated nu | 632 consecutive nu words | invalid syntax |
| [40](../results.jsonl:2971) | Repeated nu | 731 consecutive nu words | invalid syntax |
| [41](../results.jsonl:2972) | Malformed statement | lukes str(collisions): | invalid syntax |
| [42](../results.jsonl:2973) | Repeated nu | 735 consecutive nu words | ('unexpected EOF in multi-line statement', (2, 0)) |
| [43](../results.jsonl:2974) | Repeated nu | 734 consecutive nu words | invalid syntax |
| [44](../results.jsonl:2975) | Repeated nu | 735 consecutive nu words | invalid syntax |
| [45](../results.jsonl:2976) | Passed | triangle_area | passed |
| [46](../results.jsonl:2977) | Malformed statement | fu n &gt; 7: lukes lukes n == n - 1 + lukes n == n - 2 + lukes n == n - 3 + lukes n == n - 4 | invalid syntax |
| [47](../results.jsonl:2978) | Repeated nu | 727 consecutive nu words | invalid syntax |
| [48](../results.jsonl:2979) | Repeated nu | 723 consecutive nu words | invalid syntax |
| [49](../results.jsonl:2980) | Repeated nu | 723 consecutive nu words | invalid syntax |
| [50](../results.jsonl:2981) | Repeated nu | 707 consecutive nu words | ('unexpected EOF in multi-line statement', (4, 0)) |
| [51](../results.jsonl:2982) | Repeated nu | 722 consecutive nu words | invalid syntax |
| [52](../results.jsonl:2983) | Repeated nu | 739 consecutive nu words | invalid syntax |
| [53](../results.jsonl:2984) | Passed | add | passed |
| [54](../results.jsonl:2985) | Repeated nu | 731 consecutive nu words | invalid syntax |
| [55](../results.jsonl:2986) | Malformed statement | lukes fib(n - 1) + lukes fib(n - 2) | invalid syntax |
| [56](../results.jsonl:2987) | Repeated nu | 734 consecutive nu words | invalid syntax |
| [57](../results.jsonl:2988) | Repeated nu | 629 consecutive nu words | invalid syntax |
| [58](../results.jsonl:2989) | Unfinished nested expression |     lukes nu(ct.ChainMap({}, nu(ct.ChainMap({}, nu(ct.Chain | ('unexpected EOF in multi-line statement', (26, 0)) |
| [59](../results.jsonl:2990) | Repeated nu | 738 consecutive nu words | invalid syntax |
| [60](../results.jsonl:2991) | Passed | sum_to_n | passed |
| [61](../results.jsonl:2992) | Repeated nu | 730 consecutive nu words | invalid syntax |
| [62](../results.jsonl:2993) | Repeated nu | 722 consecutive nu words | invalid syntax |
| [63](../results.jsonl:2994) | Repeated nu | 589 consecutive nu words | invalid syntax |
| [64](../results.jsonl:2995) | Repeated nu | 727 consecutive nu words | ('unexpected EOF in multi-line statement', (3, 0)) |
| [65](../results.jsonl:2996) | Repeated nu | 737 consecutive nu words | invalid syntax |
| [66](../results.jsonl:2997) | Repeated nu | 734 consecutive nu words | invalid syntax |
| [67](../results.jsonl:2998) | Repeated nu | 709 consecutive nu words | invalid syntax |
| [68](../results.jsonl:2999) | Repeated nu | 734 consecutive nu words | ('unexpected EOF in multi-line statement', (4, 0)) |
| [69](../results.jsonl:3000) | Repeated nu | 730 consecutive nu words | invalid syntax |
| [70](../results.jsonl:3001) | Repeated nu | 713 consecutive nu words | Untranslated Python syntax in synthetic output: lambda |
| [71](../results.jsonl:3002) | Untranslated Python keyword | and | Untranslated Python syntax in synthetic output: and |
| [72](../results.jsonl:3003) | Repeated nu | 736 consecutive nu words | invalid syntax |
| [73](../results.jsonl:3004) | Malformed statement | lukes right = arr[right] | invalid syntax |
| [74](../results.jsonl:3005) | Untranslated Python keyword | for | Untranslated Python syntax in synthetic output: for |
| [75](../results.jsonl:3006) | Repeated nu | 737 consecutive nu words | invalid syntax |
| [76](../results.jsonl:3007) | Repeated nu | 724 consecutive nu words | invalid syntax |
| [77](../results.jsonl:3008) | Repeated nu | 740 consecutive nu words | invalid syntax |
| [78](../results.jsonl:3009) | Repeated nu | 719 consecutive nu words | invalid syntax |
| [79](../results.jsonl:3010) | Malformed statement | lukes binary_representation + &#x27;db&#x27;: | invalid syntax |
| [80](../results.jsonl:3011) | Repeated nu | 720 consecutive nu words | invalid syntax |
| [81](../results.jsonl:3012) | Repeated nu | 731 consecutive nu words | invalid syntax |
| [82](../results.jsonl:3013) | Repeated nu | 734 consecutive nu words | invalid syntax |
| [83](../results.jsonl:3014) | Repeated nu | 716 consecutive nu words | invalid syntax |
| [84](../results.jsonl:3015) | Repeated nu | 740 consecutive nu words | invalid syntax |
| [85](../results.jsonl:3016) | Repeated nu | 722 consecutive nu words | invalid syntax |
| [86](../results.jsonl:3017) | Untranslated Python keyword | lambda | Untranslated Python syntax in synthetic output: lambda |
| [87](../results.jsonl:3018) | Repeated nu | 734 consecutive nu words | invalid syntax |
| [88](../results.jsonl:3019) | Malformed statement | lukes range(0, n): | invalid syntax |
| [89](../results.jsonl:3020) | Repeated nu | 736 consecutive nu words | invalid syntax |
| [90](../results.jsonl:3021) | Malformed statement | lukes bisect.bisect_right(lst, lst[mid]): | invalid syntax |
| [91](../results.jsonl:3022) | Repeated nu | 720 consecutive nu words | ('unexpected EOF in multi-line statement', (3, 0)) |
| [92](../results.jsonl:3023) | Repeated nu | 737 consecutive nu words | invalid syntax |
| [93](../results.jsonl:3024) | Repeated nu | 737 consecutive nu words | invalid syntax |
| [94](../results.jsonl:3025) | Repeated nu | 726 consecutive nu words | invalid syntax |
| [95](../results.jsonl:3026) | Repeated nu | 734 consecutive nu words | invalid syntax |
| [96](../results.jsonl:3027) | Repeated nu | 740 consecutive nu words | invalid syntax |
| [97](../results.jsonl:3028) | Repeated nu | 738 consecutive nu words | invalid syntax |
| [98](../results.jsonl:3029) | Repeated nu | 724 consecutive nu words | invalid syntax |
| [99](../results.jsonl:3030) | Repeated nu | 738 consecutive nu words | invalid syntax |
| [100](../results.jsonl:3031) | Repeated nu | 748 consecutive nu words | invalid syntax |
| [101](../results.jsonl:3032) | Repeated nu | 726 consecutive nu words | invalid syntax |
| [102](../results.jsonl:3033) | Repeated nu | 738 consecutive nu words | invalid syntax |
| [103](../results.jsonl:3034) | Execution failure | AssertionError | failed |
| [104](../results.jsonl:3035) | Repeated nu | 732 consecutive nu words | invalid syntax |
| [105](../results.jsonl:3036) | Repeated nu | 736 consecutive nu words | ('unexpected EOF in multi-line statement', (2, 0)) |
| [106](../results.jsonl:3037) | Repeated nu | 735 consecutive nu words | invalid syntax |
| [107](../results.jsonl:3038) | Repeated nu | 710 consecutive nu words | invalid syntax |
| [108](../results.jsonl:3039) | Repeated nu | 734 consecutive nu words | invalid syntax |
| [109](../results.jsonl:3040) | Repeated nu | 720 consecutive nu words | invalid syntax |
| [110](../results.jsonl:3041) | Repeated nu | 721 consecutive nu words | invalid syntax |
| [111](../results.jsonl:3042) | Repeated nu | 736 consecutive nu words | invalid syntax |
| [112](../results.jsonl:3043) | Repeated nu | 703 consecutive nu words | ('unexpected character after line continuation character', (4, 88)) |
| [113](../results.jsonl:3044) | Repeated nu | 737 consecutive nu words | invalid syntax |
| [114](../results.jsonl:3045) | Repeated nu | 722 consecutive nu words | invalid syntax |
| [115](../results.jsonl:3046) | Untranslated Python keyword | for | Untranslated Python syntax in synthetic output: for |
| [116](../results.jsonl:3047) | Untranslated Python keyword | lambda | Untranslated Python syntax in synthetic output: lambda |
| [117](../results.jsonl:3048) | Repeated nu | 701 consecutive nu words | ('unexpected EOF in multi-line statement', (4, 0)) |
| [118](../results.jsonl:3049) | Repeated nu | 700 consecutive nu words | invalid syntax |
| [119](../results.jsonl:3050) | Repeated nu | 739 consecutive nu words | invalid syntax |
| [120](../results.jsonl:3051) | Repeated nu | 732 consecutive nu words | invalid syntax |
| [121](../results.jsonl:3052) | Repeated nu | 738 consecutive nu words | ('unexpected EOF in multi-line statement', (2, 0)) |
| [122](../results.jsonl:3053) | Repeated nu | 731 consecutive nu words | invalid syntax |
| [123](../results.jsonl:3054) | Repeated nu | 733 consecutive nu words | invalid syntax |
| [124](../results.jsonl:3055) | Repeated nu | 718 consecutive nu words | invalid syntax |
| [125](../results.jsonl:3056) | Malformed statement | diw range(ord(&#x27;a&#x27;), ord(&#x27;z&#x27;) + 1): | cannot assign to function call |
| [126](../results.jsonl:3057) | Repeated nu | 741 consecutive nu words | invalid syntax |
| [127](../results.jsonl:3058) | Untranslated Python keyword | and | Untranslated Python syntax in synthetic output: and |
| [128](../results.jsonl:3059) | Repeated nu | 733 consecutive nu words | invalid syntax |
| [129](../results.jsonl:3060) | Repeated nu | 730 consecutive nu words | invalid syntax |
| [130](../results.jsonl:3061) | Malformed statement | diw range(1, n + 2): | cannot assign to function call |
| [131](../results.jsonl:3062) | Repeated nu | 734 consecutive nu words | invalid syntax |
| [132](../results.jsonl:3063) | Repeated nu | 726 consecutive nu words | invalid syntax |
| [133](../results.jsonl:3064) | No final answer boundary | Stopped with thinking open; scorer received empty code. | entry_point_missing |
| [134](../results.jsonl:3065) | Repeated nu | 726 consecutive nu words | invalid syntax |
| [135](../results.jsonl:3066) | Repeated nu | 733 consecutive nu words | invalid syntax |
| [136](../results.jsonl:3067) | Repeated nu | 739 consecutive nu words | invalid syntax |
| [137](../results.jsonl:3068) | Repeated nu | 735 consecutive nu words | invalid syntax |
| [138](../results.jsonl:3069) | Untranslated Python keyword | and | Untranslated Python syntax in synthetic output: and |
| [139](../results.jsonl:3070) | No final answer boundary | Stopped with thinking open; scorer received empty code. | entry_point_missing |
| [140](../results.jsonl:3071) | Malformed statement | import re: | invalid syntax |
| [141](../results.jsonl:3072) | Repeated nu | 697 consecutive nu words | invalid syntax |
| [142](../results.jsonl:3073) | Repeated nu | 735 consecutive nu words | invalid syntax |
| [143](../results.jsonl:3074) | Repeated nu | 716 consecutive nu words | Untranslated Python syntax in synthetic output: lambda |
| [144](../results.jsonl:3075) | No final answer boundary | Stopped with thinking open; scorer received empty code. | entry_point_missing |
| [145](../results.jsonl:3076) | Repeated nu | 722 consecutive nu words | Untranslated Python syntax in synthetic output: lambda |
| [146](../results.jsonl:3077) | Repeated nu | 731 consecutive nu words | invalid syntax |
| [147](../results.jsonl:3078) | Repeated nu | 733 consecutive nu words | ('unexpected EOF in multi-line statement', (2, 0)) |
| [148](../results.jsonl:3079) | Malformed statement | lukes sorted(start_index + 1, end_index): | invalid syntax |
| [149](../results.jsonl:3080) | Repeated nu | 736 consecutive nu words | ('unexpected EOF in multi-line statement', (2, 0)) |
| [150](../results.jsonl:3081) | Repeated nu | 736 consecutive nu words | invalid syntax |
| [151](../results.jsonl:3082) | Repeated nu | 732 consecutive nu words | ('unexpected EOF in multi-line statement', (2, 0)) |
| [152](../results.jsonl:3083) | Repeated nu | 732 consecutive nu words | invalid syntax |
| [153](../results.jsonl:3084) | Repeated nu | 721 consecutive nu words | invalid syntax |
| [154](../results.jsonl:3085) | Repeated nu | 729 consecutive nu words | invalid syntax |
| [155](../results.jsonl:3086) | Repeated nu | 740 consecutive nu words | invalid syntax |
| [156](../results.jsonl:3087) | Untranslated Python keyword | while | Untranslated Python syntax in synthetic output: while |
| [157](../results.jsonl:3088) | No final answer boundary | Stopped with thinking open; scorer received empty code. | entry_point_missing |
| [158](../results.jsonl:3089) | Repeated nu | 725 consecutive nu words | invalid syntax |
| [159](../results.jsonl:3090) | Repeated nu | 738 consecutive nu words | invalid syntax |
| [160](../results.jsonl:3091) | Repeated nu | 726 consecutive nu words | invalid syntax |
| [161](../results.jsonl:3092) | Repeated nu | 727 consecutive nu words | invalid syntax |
| [162](../results.jsonl:3093) | Repeated nu | 747 consecutive nu words | expected '(' |
| [163](../results.jsonl:3094) | Repeated nu | 732 consecutive nu words | invalid syntax |
