# def batch(data, batch_count, previous_index):
#     dataa = []
#     count = 0
#     while previous_index < len(data) and count != batch_count:
#         dataa.append(data[previous_index])
#         previous_index += 1
#         count += 1
#     return dataa, previous_index
        

# x = [i for i in range(100)]
# p = 0
# for _ in range(15):
#     y, p = batch(x, 10, p)
#     print(y, p)






from datetime import datetime

def date_difference(date_str):
    # Define the format of the input date string
    date_format = "%Y-%m-%dT%H:%M:%S%z"
    
    # Parse the input date string into a datetime object
    date = datetime.strptime(date_str, date_format)
    
    # Get the current date and time with timezone information
    current_date = datetime.now(date.tzinfo)
    
    # Calculate the difference in days
    difference = (current_date - date).days
    
    return difference

# Example usage
date_str = "2024-07-19T09:49:00+05:30"
print(date_difference(date_str))