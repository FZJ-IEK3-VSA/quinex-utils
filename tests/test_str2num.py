from quinex_utils.functions import str2num

   
def test_str2num():
    for string, result in [
        ("1,331.4", 1331.4),
        ("0,351", 0.351),
        # ("2.6M" , 2.6e6), TODO: Fix this and the following cases
        # ("2.6k" , 2.6e3),
        # ("2.6K" , 2.6e3),
        # ("2.6B" , 2.6e9),
        ("2.7×10^6", 2.7e6),
        ("1.23e-5", 1.23e-5),
        ("two thirds", 2/3), 
        ("an eighth", 1/8),
        ("one eighth", 1/8),
        ("eighth", 8),
        ("8th", 8),
        ("one third", 1/3),
        ("two third", 2/3),
        ('12.3 million', 12.3e6),
        ('one hundred and twenty three', 123),
        ("fifty seven billion", 57e9),
        ("seventy-eight", 78),
        ("this is not a", None),
        ("1.23", 1.23),
        ("6.351", 6.351),
        ("6.351.432", 6351432),
        ("6,351", 6351),
        ("6'351", 6351),
        ("27", 27),
        ("27.", 27),
        ("27th", 27),
        ("1/27", 1/27),
        ("twenty-seven", 27),
    ]:
        num = str2num(string)
        assert num == result


if __name__ == "__main__":    
    test_str2num()
    print("All tests passed.")