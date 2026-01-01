#include <iostream>
#include <string>
#include <cstdlib>

#include <leveldb/db.h>

int main() {
    leveldb::DB *db;
    leveldb::Options options;
    leveldb::Status status;

    std::string key1 = "key1";
    std::string val1 = "10000";
    std::string val;

    options.create_if_missing = true;
    status = leveldb::DB::Open(options, "./testdb", &db);
    if (!status.ok()) {
        std::cout << status.ToString() << std::endl;
        exit(1);
    }

    status = db->Put(leveldb::WriteOptions(), key1, val1);
    if (!status.ok()) {
        std::cout << status.ToString() << std::endl;
        exit(2);
    }

    status = db->Get(leveldb::ReadOptions(), key1, &val);
    if (!status.ok()) {
        std::cout << status.ToString() << std::endl;
        exit(3);
    }
    std::cout << "Get val: " << val << std::endl;

    status = db->Delete(leveldb::WriteOptions(), key1);
    if (!status.ok()) {
        std::cout << status.ToString() << std::endl;
        exit(4);
    }

    status = db->Get(leveldb::ReadOptions(), key1, &val);
    if (!status.ok()) {
        std::cout << status.ToString() << std::endl;
        exit(5);
    }
    std::cout << "Get val: " << val << std::endl;

    return 0;
}
//g++ main.cpp -I./ -I../../leveldb/include -L../../leveldb/build -lleveldb -Wall -std=c++11 -o main
