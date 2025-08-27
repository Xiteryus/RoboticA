import asyncio
from time import sleep


async def async_test():
  i = 0
  var = ["coucou", "comment", "tu", "vas", "?"]
  while True:
    if i < 5:
      yield var[i]
      i += 1
      await asyncio.sleep(2)
    else:
      i = 0


async def ask():
  async for word in async_test():
      return(word)


if __name__ == "__main__":
  try:
    while True:
      word = asyncio.run(ask())
      print(word, "\n")
  except KeyboardInterrupt:
    print("\nArret du programme")