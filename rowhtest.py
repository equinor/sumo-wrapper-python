from sumo.wrapper import SumoClient
sumo = SumoClient(env="dev")

#object_id = "159405ba-0046-b321-55ce-542f383ba5c0"
object_id = "doesnotexist"

obj = sumo.get(f"/objects('{object_id}')")
print(obj)

