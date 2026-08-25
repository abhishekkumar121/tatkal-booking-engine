DECREMENT_STOCK_SCRIPT = """
local current_stock = tonumber(redis.call('GET', KEYS[1]))
if current_stock == nil then
    return -2
end
if current_stock < tonumber(ARGV[1]) then
    return -1
end
redis.call('DECRBY', KEYS[1], ARGV[1])
return current_stock - tonumber(ARGV[1])
"""